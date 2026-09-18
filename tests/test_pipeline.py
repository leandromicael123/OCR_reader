"""Respostas sintéticas explícitas: testa o pipeline, não precisão OCR."""
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image
import pytest

from ocr_reader.config import Settings, initialize
from ocr_reader.exporters.files import verify_bundle, write_json
from ocr_reader.pipeline import process_batch
from ocr_reader.storage.state import State


FAST = Settings(stable_interval_seconds=0)


class SyntheticBackend:
    fingerprint = "synthetic-test-only:1"

    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def check(self):
        pass

    def recognize(self, image, output):
        self.calls += 1
        if self.fail:
            raise RuntimeError("Falha sintética intencional.")
        raw = {"parsing_res_list": [
            {"block_label": "text", "block_content": "Teste sintético — não é OCR real.",
             "block_bbox": [0, 0, 30, 20]},
            {"block_label": "formula", "block_content": r"\frac{x+1}{x-2}",
             "block_bbox": [0, 20, 30, 40]},
            {"block_label": "code", "block_content": "if x = 1:\n    y += 2  \n\n    # erro original",
             "block_bbox": [0, 40, 60, 70]}]}
        output.mkdir()
        write_json(output / "paddle-result.json", raw)
        return raw


@pytest.fixture
def workspace(tmp_path):
    project = tmp_path / "project"
    initialize(project)
    state = tmp_path / "state"
    return project, state


def create_image(path, color="white"):
    Image.new("RGB", (100, 100), color).save(path)


def run(workspace, backend, **kwargs):
    return process_batch(*workspace, FAST, backend, emit=lambda _: None, **kwargs)


def bundle(project):
    return next((project / "Resultado").glob("*/manifest.json")).parent


def test_full_pipeline_preserves_original_and_code(workspace):
    project, _ = workspace
    source = project / "Entrada" / "pagina_001.png"
    create_image(source)
    original_bytes = source.read_bytes()
    backend = SyntheticBackend()
    counts = run(workspace, backend)
    assert counts["completed"] == 1 and backend.calls == 1
    output = bundle(project)
    doc = json.loads((output / "transcricao.json").read_text(encoding="utf-8"))
    assert source.read_bytes() == original_bytes == (output / "original.png").read_bytes()
    assert doc["review"]["status"] == "required"
    assert doc["blocks"][2]["text"] == "if x = 1:\n    y += 2  \n\n    # erro original"
    assert doc["blocks"][1]["latex"] == r"\frac{x+1}{x-2}"
    assert verify_bundle(output, hashlib.sha256(original_bytes).hexdigest(), doc["job_id"])
    assert "preview.html" in (project / "ParaRever" / "index.html").read_text(encoding="utf-8")
    assert not list((project / "Processados").iterdir())


def test_duplicate_under_another_name_does_not_repeat_ocr(workspace):
    project, _ = workspace
    a = project / "Entrada" / "a.png"
    create_image(a)
    shutil.copyfile(a, a.with_name("b.png"))
    backend = SyntheticBackend()
    result = run(workspace, backend)
    assert result["completed"] == 1 and result["duplicates"] == 1 and backend.calls == 1
    result = run(workspace, backend)
    assert result["duplicates"] == 2 and backend.calls == 1


def test_changed_content_same_name_creates_new_result(workspace):
    project, _ = workspace
    source = project / "Entrada" / "same.png"
    backend = SyntheticBackend()
    create_image(source, "white")
    run(workspace, backend)
    create_image(source, "black")
    run(workspace, backend)
    assert backend.calls == 2
    assert len(list((project / "Resultado").glob("*/manifest.json"))) == 2


def test_failures_require_explicit_retry(workspace):
    project, _ = workspace
    create_image(project / "Entrada" / "a.png")
    backend = SyntheticBackend(fail=True)
    assert run(workspace, backend)["failed"] == 1
    assert run(workspace, backend)["pending_retry"] == 1
    assert backend.calls == 1
    backend.fail = False
    assert run(workspace, backend, retry_failed=True)["completed"] == 1
    assert backend.calls == 2


def test_tampered_output_is_not_silently_replaced(workspace):
    project, _ = workspace
    create_image(project / "Entrada" / "a.png")
    backend = SyntheticBackend()
    run(workspace, backend)
    output = bundle(project)
    (output / "transcricao.md").write_text("Correção humana", encoding="utf-8")
    assert run(workspace, backend)["pending_retry"] == 1
    assert backend.calls == 1
    assert run(workspace, backend, retry_failed=True)["completed"] == 1
    assert (output / "transcricao.md").read_text(encoding="utf-8") == "Correção humana"


def test_recovery_after_rename_before_database_commit(workspace, monkeypatch):
    project, state_dir = workspace
    create_image(project / "Entrada" / "a.png")
    backend = SyntheticBackend()
    real_update = State.update

    def crash(self, job_id, status, error_code=None):
        if status == "needs_review":
            raise SystemExit("Simulação de encerramento após rename")
        return real_update(self, job_id, status, error_code)

    monkeypatch.setattr(State, "update", crash)
    with pytest.raises(SystemExit):
        run(workspace, backend)
    monkeypatch.setattr(State, "update", real_update)
    result = run(workspace, backend)
    assert result["duplicates"] == 1 and backend.calls == 1
    state = State(state_dir)
    try:
        assert state.rows()[0]["status"] == "needs_review"
    finally:
        state.close()


def test_force_preserves_previous_result(workspace):
    project, _ = workspace
    create_image(project / "Entrada" / "a.png")
    backend = SyntheticBackend()
    run(workspace, backend)
    assert run(workspace, backend, force=True)["completed"] == 1
    assert len(list((project / "Resultado").glob("*/manifest.json"))) == 2


def test_valid_bundle_recovers_even_if_final_state_write_failed(workspace):
    project, state_dir = workspace
    create_image(project / "Entrada" / "a.png")
    backend = SyntheticBackend()
    run(workspace, backend)
    state = State(state_dir)
    try:
        state.update(state.rows()[0]["id"], "failed", "OperationalError")
    finally:
        state.close()
    assert run(workspace, backend)["duplicates"] == 1
    assert backend.calls == 1


def test_interrupted_before_export_requires_retry(workspace):
    project, state_dir = workspace
    source = project / "Entrada" / "a.png"
    create_image(source)
    backend = SyntheticBackend()
    state = State(state_dir)
    try:
        state.create("old-job", hashlib.sha256(source.read_bytes()).hexdigest(), backend.fingerprint,
                     source.name, "Resultado/never-committed")
    finally:
        state.close()
    assert run(workspace, backend)["pending_retry"] == 1
    assert backend.calls == 0
    assert run(workspace, backend, retry_failed=True)["completed"] == 1


def test_limit_counts_inferences_not_duplicates(workspace):
    project, _ = workspace
    create_image(project / "Entrada" / "a.png", "white")
    create_image(project / "Entrada" / "b.png", "black")
    backend = SyntheticBackend()
    assert run(workspace, backend, limit=1)["completed"] == 1
    counts = run(workspace, backend, limit=1)
    assert counts["completed"] == 1 and counts["duplicates"] == 1


def test_corrupt_image_does_not_call_ocr_or_remove_original(workspace):
    project, _ = workspace
    source = project / "Entrada" / "corrupt.png"
    source.write_bytes(b"not an image")
    backend = SyntheticBackend()
    assert run(workspace, backend)["failed"] == 1
    assert backend.calls == 0 and source.read_bytes() == b"not an image"
    assert len(list((project / "Erros").glob("*.json"))) == 1


def test_corrupt_page_does_not_block_other_pages(workspace):
    project, _ = workspace
    (project / "Entrada" / "1.png").write_bytes(b"bad")
    create_image(project / "Entrada" / "2.png")
    counts = run(workspace, SyntheticBackend())
    assert counts["failed"] == 1 and counts["completed"] == 1
