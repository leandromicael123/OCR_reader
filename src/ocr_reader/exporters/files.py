from pathlib import Path
import html
import json
import os
import re

from ocr_reader.ingestion.images import sha256_file


def write_text(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    temporary.replace(path)


def write_json(path: Path, value: dict) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def markdown(document: dict, original: str) -> str:
    lines = ["# Transcrição por rever", "",
             "> Texto produzido automaticamente. Compare com a imagem original.", ""]
    for block in document["blocks"]:
        content = block["text"]  # Não aparar espaços, corrigir código ou reformular frases.
        kind = block["type"]
        if kind == "code":
            longest = max((len(x) for x in re.findall(r"`+", content)), default=0)
            fence = "`" * max(3, longest + 1)
            lines.append(f"{fence}\n{content}\n{fence}")
        elif kind == "equation":
            lines.append("$$\n" + block["latex"] + "\n$$")
        elif kind == "heading":
            lines.append("## " + content)
        else:
            lines.append(content)
        if kind in {"diagram", "unknown"} and block.get("source_crop"):
            lines.append(f"![Recorte do original]({block['source_crop']})")
        lines.append("")
    lines.extend(["---", "", "## Evidência e avisos", "",
                  f"[Imagem original]({original})", "",
                  "- Estado: revisão humana necessária."])
    lines.extend("- " + warning for warning in document["warnings"])
    for block in document["blocks"]:
        lines.extend(f"- {block['id']}: {w}" for w in block["warnings"])
    return "\n".join(lines) + "\n"


def preview(document: dict) -> str:
    sections = []
    for block in document["blocks"]:
        crop = (f'<img src="{html.escape(block["source_crop"], quote=True)}" alt="Recorte original" />'
                if block.get("source_crop") else "")
        warnings = " ".join(block["warnings"])
        sections.append(
            f'<article><h2>{block["id"]} · {html.escape(block["type"])}</h2>'
            f'{crop}<pre>{html.escape(block["text"])}</pre>'
            f'<p class="warning">{html.escape(warnings)}</p></article>')
    return '''<!doctype html><html lang="pt-PT"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>OCR_reader · Revisão</title><style>
body{margin:0;font:16px/1.5 system-ui,sans-serif;color:#19334b;background:#f1f5f9}
header{padding:20px;background:#153b55;color:white}h1{font-size:24px;margin:0}
main{display:grid;grid-template-columns:1fr 1fr;gap:20px;padding:20px}
.page img{width:100%;height:auto}.page{position:sticky;top:20px;align-self:start}
article{background:white;padding:18px;margin-bottom:16px;border-radius:8px}
article img{max-width:100%;max-height:240px;object-fit:contain}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7fa;padding:12px}
.warning{color:#805208}h2{font-size:17px}a{color:#075985}
@media(max-width:850px){main{grid-template-columns:1fr}.page{position:static}}
</style></head><body><header><h1>Transcrição por rever</h1>
<p>Compare todos os blocos com o original. As fórmulas são mostradas em LaTeX literal.
Esta página não executa código nem carrega serviços externos.</p></header><main>
<section class="page"><img src="normalized.png" alt="Página original com orientação EXIF aplicada"></section>
<section>''' + "".join(sections) + '</section></main></body></html>'


def export_document(directory: Path, document: dict, original: str) -> None:
    write_json(directory / "transcricao.json", document)
    write_text(directory / "transcricao.md", markdown(document, original))
    write_text(directory / "preview.html", preview(document))
    files = {p.relative_to(directory).as_posix(): sha256_file(p)
             for p in sorted(directory.rglob("*")) if p.is_file() and p.name != "manifest.json"}
    write_json(directory / "manifest.json", {"schema_version": "1.0", "job_id": document["job_id"],
                                             "sha256": document["source"]["sha256"], "files": files})


def verify_bundle(directory: Path, expected_hash: str, expected_job: str) -> bool:
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("sha256") != expected_hash or manifest.get("job_id") != expected_job:
            return False
        files = manifest["files"]
        if not isinstance(files, dict) or not {"transcricao.json", "transcricao.md", "preview.html", "normalized.png"} <= set(files):
            return False
        if not any(name.startswith("original.") for name in files):
            return False
        for name, digest in files.items():
            path = (directory / name).resolve()
            if not path.is_relative_to(directory.resolve()) or not path.is_file():
                return False
            if sha256_file(path) != digest:
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False

