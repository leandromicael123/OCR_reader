import argparse
import json
from pathlib import Path
import sys
import tempfile
import sqlite3

from ocr_reader.config import Settings, initialize, state_directory
from ocr_reader.recognition.paddle import BackendUnavailable, PaddleBackend, diagnostics


def default_project() -> Path:
    return Path(__file__).resolve().parents[2]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="OCR_reader: transcrição local de imagens JPG/PNG.")
    parser.add_argument("--project", type=Path, default=default_project(), help="Pasta do projeto/dados")
    parser.add_argument("--state-dir", type=Path, help="SQLite local; por defeito fica fora do projeto")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Criar pastas sem descarregar modelos")
    sub.add_parser("doctor", help="Diagnosticar hardware e dependências; não carrega o modelo")
    sub.add_parser("check", help="Validar imagens sem reconhecer nem descarregar modelos")
    run = sub.add_parser("process", help="Reconhecer um lote local e gerar ficheiros para revisão")
    run.add_argument("--limit", type=int, help="Máximo de novas inferências")
    run.add_argument("--retry-failed", action="store_true", help="Repetir trabalhos falhados/interrompidos")
    run.add_argument("--force", action="store_true", help="Criar nova execução mesmo para conteúdo conhecido")
    sub.add_parser("status", help="Consultar trabalhos persistidos")
    args = parser.parse_args(argv)
    project = args.project.resolve()
    state_dir = args.state_dir.resolve() if args.state_dir else state_directory(project)
    try:
        if args.command == "doctor":
            report = diagnostics()
            report["project"] = str(project)
            report["state_directory"] = str(state_dir)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if report["arm_host"]:
                print("Perfil OCR inicial: executar no computador Intel/AMD x64, não neste ARM emulado.")
            elif not report["ready_to_try_ocr"]:
                print("Instale as dependências com scripts/install.ps1 -WithOCR no computador Intel.")
            return 0 if report["ready_to_try_ocr"] else 2
        settings = Settings.load(project)
        initialize(project)
        if args.command == "init":
            print(f"Pastas preparadas em {project}. Coloque imagens em Entrada.")
            return 0
        if args.command == "check":
            from ocr_reader.ingestion.images import acquire, discover
            files = discover(project / "Entrada")
            failed = 0
            for path in files:
                try:
                    with tempfile.TemporaryDirectory(prefix=".check-", dir=project / "Resultado") as tmp:
                        snap = acquire(path, Path(tmp), settings)
                        print(f"OK: {path.name} | {snap.width}x{snap.height} | SHA256 {snap.sha256[:12]}")
                except Exception as exc:
                    failed += 1
                    print(f"Por verificar: {path.name} | {type(exc).__name__}")
            print(f"{len(files)} imagem(ns); {failed} por verificar. Não foi executado OCR.")
            return 1 if failed else 0
        if args.command == "status":
            if not (state_dir / "state.sqlite").is_file():
                print("Ainda não existem trabalhos registados nesta instalação.")
                return 0
            from ocr_reader.storage.state import State
            state = State(state_dir)
            try:
                print(json.dumps(state.rows(), ensure_ascii=False, indent=2))
            finally:
                state.close()
            return 0
        if args.limit is not None and args.limit < 1:
            parser.error("--limit deve ser positivo")
        from ocr_reader.pipeline import process_batch
        result = process_batch(project, state_dir, settings, PaddleBackend(settings),
                               limit=args.limit, retry_failed=args.retry_failed, force=args.force)
        print(json.dumps(result, ensure_ascii=False))
        return 1 if result["failed"] or result["waiting"] or result["pending_retry"] else 0
    except BackendUnavailable as exc:
        print(f"OCR indisponível: {exc}", file=sys.stderr)
        return 2
    except (ValueError, TypeError, RuntimeError, OSError, sqlite3.Error) as exc:
        print(f"Não foi possível executar: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrompido. Originais conservados; repetir com --retry-failed.", file=sys.stderr)
        return 130
