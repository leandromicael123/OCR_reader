from datetime import datetime, timezone
from pathlib import Path
import math

from PIL import Image


LABELS = {"doc_title": "heading", "paragraph_title": "heading", "text": "paragraph",
          "content": "paragraph", "formula": "equation", "display_formula": "equation",
          "code": "code", "table": "table", "image": "diagram", "chart": "diagram",
          "figure": "diagram", "list": "list", "reference": "paragraph",
          "footnote": "annotation", "header": "annotation", "footer": "annotation",
          "aside_text": "annotation", "number": "annotation"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(raw: dict, *, job_id: str, original_name: str, sha256: str,
              fingerprint: str, normalized: Path, output: Path, duration: float) -> dict:
    entries = raw.get("parsing_res_list")
    if not isinstance(entries, list) or len(entries) > 1000:
        raise ValueError("Lista de blocos inválida ou excessiva.")
    blocks = []
    warnings = ["Transcrição automática não revista; verificar omissões e símbolos."]
    if not entries:
        warnings.append("O motor não detetou blocos. A página não foi considerada transcrita.")
    assets = output / "assets"
    assets.mkdir(exist_ok=True)
    with Image.open(normalized) as image:
        width, height = image.size
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict) or not isinstance(entry.get("block_content"), str):
                raise ValueError("Bloco sem conteúdo textual válido; não é seguro omiti-lo.")
            label = entry.get("block_label", "unknown")
            if not isinstance(label, str):
                raise ValueError("Etiqueta de bloco inválida.")
            kind = LABELS.get(label, "unknown")
            bbox = entry.get("block_bbox")
            valid_bbox = (isinstance(bbox, list) and len(bbox) == 4
                          and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                  and math.isfinite(v) for v in bbox))
            if valid_bbox:
                x1, y1, x2, y2 = bbox
                valid_bbox = 0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height
            block = {"id": f"b{index + 1}", "order": index + 1, "type": kind,
                     "source_label": label, "text": entry["block_content"],
                     "bbox": bbox if valid_bbox else None, "confidence": None,
                     "review_status": "required", "warnings": []}
            if kind == "unknown":
                block["warnings"].append("Tipo não mapeado; conteúdo conservado sem interpretação.")
            if not valid_bbox:
                block["warnings"].append("Região inválida/ausente; comparar com a página completa.")
            else:
                crop_name = f"assets/{block['id']}-original.png"
                image.crop(tuple(bbox)).save(output / crop_name)
                block["source_crop"] = crop_name
            if kind == "equation":
                latex = entry["block_content"]
                for opening, closing in (("$$", "$$"), (r"\[", r"\]")):
                    if latex.startswith(opening) and latex.endswith(closing) and len(latex) >= len(opening + closing):
                        latex = latex[len(opening):-len(closing)]
                        break
                block["latex"] = latex
                block["warnings"].append("LaTeX não validado visualmente; não é uma expressão aprovada.")
            blocks.append(block)
    return {"schema_version": "1.0", "job_id": job_id, "created_at": utc_now(),
            "source": {"original_name": original_name, "sha256": sha256,
                       "width": width, "height": height,
                       "coordinate_space": "normalized_image_pixels",
                       "transform": "EXIF transpose; composite alpha on white; original bytes retained"},
            "recognition": {"engine": fingerprint, "duration_seconds": round(duration, 3)},
            "blocks": blocks, "warnings": warnings,
            "review": {"status": "required"}}

