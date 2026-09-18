from pathlib import Path
import html
import tempfile
import time
import uuid

from ocr_reader.config import Settings, initialize
from ocr_reader.exporters.files import export_document, verify_bundle, write_json, write_text
from ocr_reader.ingestion.images import InvalidImage, WaitingForFile, acquire, discover
from ocr_reader.processing.document import normalize
from ocr_reader.storage.state import State, instance_lock, log_event


def review_index(project: Path, state: State):
    rows = []
    for row in state.rows():
        if row["status"] != "needs_review":
            continue
        target = "../" + row["output_rel"] + "/preview.html"
        rows.append(f'<li><a href="{html.escape(target, quote=True)}">'
                    f'{html.escape(row["source_name"])} · {row["id"][:8]}</a></li>')
    write_text(project / "ParaRever" / "index.html",
               '<!doctype html><html lang="pt-PT"><meta charset="utf-8">'
               '<title>OCR_reader · Para rever</title><h1>Transcrições por rever</h1>'
               '<p>Compare com o original. A aprovação e o envio para OneNote ficam para a próxima fase.</p>'
               '<ul>' + "".join(rows) + '</ul></html>')


def process_batch(project: Path, state_dir: Path, settings: Settings, backend,
                  *, limit: int | None = None, retry_failed: bool = False,
                  force: bool = False, emit=print) -> dict:
    initialize(project)
    files = discover(project / "Entrada")
    counts = {"completed": 0, "duplicates": 0, "waiting": 0, "failed": 0, "pending_retry": 0}
    if not files:
        emit("A pasta Entrada está vazia. Adicione imagens JPG ou PNG.")
        return counts
    backend.check()  # Falha clara antes de criar trabalhos se o hardware/motor não estiver pronto.
    with instance_lock(project / "logs" / ".process.lock"):
        state = State(state_dir)
        try:
            state.recover(project)
            fingerprint = backend.fingerprint
            processed = 0
            for source in files:
                if limit is not None and processed >= limit:
                    break
                job_id = None
                with tempfile.TemporaryDirectory(prefix=".work-", dir=project / "Resultado") as temp:
                    staging = Path(temp)
                    try:
                        snapshot = acquire(source, staging, settings)
                        previous = state.latest(snapshot.sha256, fingerprint)
                        if previous and not force:
                            if verify_bundle(project / previous["output_rel"], snapshot.sha256, previous["id"]):
                                # Também recupera uma falha depois do rename (por exemplo, no log/commit).
                                if previous["status"] != "needs_review":
                                    state.update(previous["id"], "needs_review")
                                counts["duplicates"] += 1
                                emit(f"Já processado: {source.name}")
                                continue
                            if previous["status"] == "needs_review":
                                state.update(previous["id"], "failed", "ARTIFACTS_CHANGED_OR_MISSING")
                            if not retry_failed:
                                counts["pending_retry"] += 1
                                emit(f"Requer nova tentativa explícita: {source.name} (--retry-failed)")
                                continue
                        job_id = uuid.uuid4().hex
                        folder = f"{snapshot.sha256[:12]}-{job_id[:12]}"
                        output_rel = "Resultado/" + folder
                        state.create(job_id, snapshot.sha256, fingerprint, source.name, output_rel)
                        processed += 1
                        log_event(project / "logs" / "events.jsonl", "ocr_started", job_id=job_id)
                        emit(f"A reconhecer: {source.name} (pode demorar no CPU)")
                        start = time.perf_counter()
                        raw = backend.recognize(snapshot.normalized, staging / "backend")
                        duration = time.perf_counter() - start
                        document = normalize(raw, job_id=job_id, original_name=source.name,
                                             sha256=snapshot.sha256, fingerprint=fingerprint,
                                             normalized=snapshot.normalized, output=staging, duration=duration)
                        export_document(staging, document, snapshot.original.name)
                        if not verify_bundle(staging, snapshot.sha256, job_id):
                            raise ValueError("Não foi possível verificar o conjunto de resultados.")
                        # Mesmo filesystem, publicação do diretório completo de uma só vez.
                        staging.rename(project / output_rel)
                        state.update(job_id, "needs_review")
                        counts["completed"] += 1
                        log_event(project / "logs" / "events.jsonl", "result_ready", job_id=job_id,
                                  duration_seconds=round(duration, 3), blocks=len(document["blocks"]))
                        emit(f"Para rever: {output_rel}/preview.html")
                    except WaitingForFile:
                        counts["waiting"] += 1
                        emit(f"A aguardar ficheiro disponível/estável: {source.name}")
                        log_event(project / "logs" / "events.jsonl", "waiting_for_file")
                    except Exception as exc:
                        counts["failed"] += 1
                        code = "INVALID_IMAGE" if isinstance(exc, InvalidImage) else type(exc).__name__
                        if job_id:
                            state.update(job_id, "failed", code)
                        error_id = job_id or uuid.uuid4().hex
                        # Sem transcrição nem mensagens arbitrárias do motor nos logs.
                        write_json(project / "Erros" / f"{error_id}.json",
                                   {"job_id": job_id, "source_name": source.name, "error_code": code,
                                    "detail": str(exc)[:1000],
                                    "action": "Original conservado. Verificar a imagem/motor e repetir explicitamente."})
                        log_event(project / "logs" / "events.jsonl", "failed", job_id=job_id, error_code=code)
                        emit(f"Erro em {source.name}: {code}. Consulte Erros/{error_id}.json")
            review_index(project, state)
            return counts
        finally:
            state.close()
