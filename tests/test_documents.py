import json
from pathlib import Path

from PIL import Image
import pytest

from ocr_reader.processing.document import normalize
from ocr_reader.exporters.files import markdown, preview, export_document, verify_bundle


def make_document(tmp_path, entries):
    image = tmp_path / "normalized.png"
    Image.new("RGB", (100, 100)).save(image)
    return normalize({"parsing_res_list": entries}, job_id="test-job", original_name="test.png",
                     sha256="a" * 64, fingerprint="synthetic-test-only", normalized=image,
                     output=tmp_path, duration=.1)


def test_unknown_block_preserved_and_invalid_bbox_flagged(tmp_path):
    document = make_document(tmp_path, [{"block_label": "new-label", "block_content": "não omitir",
                                        "block_bbox": [-5, 0, 200, 30]}])
    block = document["blocks"][0]
    assert block["text"] == "não omitir" and block["type"] == "unknown"
    assert block["bbox"] is None and len(block["warnings"]) == 2


def test_html_escapes_recognized_content(tmp_path):
    attack = '<script>alert("x")</script><img src="https://example.com/leak">'
    document = make_document(tmp_path, [{"block_label": "text", "block_content": attack}])
    page = preview(document)
    assert "<script>" not in page
    assert "&lt;script&gt;" in page
    assert '<img src="https://' not in page
    assert document["blocks"][0]["text"] == attack


def test_code_fence_cannot_close_early_and_spaces_preserved(tmp_path):
    content = '    a = "```"  \n\n    missing ='
    document = make_document(tmp_path, [{"block_label": "code", "block_content": content}])
    md = markdown(document, "original.png")
    assert "````\n" + content + "\n````" in md


def test_empty_output_is_marked_for_review(tmp_path):
    doc = make_document(tmp_path, [])
    assert doc["review"]["status"] == "required"
    assert any("não detetou blocos" in s for s in doc["warnings"])


def test_malformed_block_is_not_dropped_silently(tmp_path):
    with pytest.raises(ValueError):
        make_document(tmp_path, [{"block_label": "text", "block_content": None}])


def test_formula_delimiters_removed_only_from_latex_field(tmp_path):
    text = "$$\\frac{1}{2}$$"
    doc = make_document(tmp_path, [{"block_label": "formula", "block_content": text}])
    assert doc["blocks"][0]["text"] == text
    assert doc["blocks"][0]["latex"] == r"\frac{1}{2}"


def test_manifest_rejects_external_path(tmp_path):
    doc = make_document(tmp_path, [{"block_label": "text", "block_content": "synthetic"}])
    (tmp_path / "original.png").write_bytes((tmp_path / "normalized.png").read_bytes())
    export_document(tmp_path, doc, "original.png")
    assert verify_bundle(tmp_path, "a" * 64, "test-job")
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["../outside.txt"] = "b" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert not verify_bundle(tmp_path, "a" * 64, "test-job")

