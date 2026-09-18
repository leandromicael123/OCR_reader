import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ocr_reader.cli import main
from ocr_reader.config import Settings
from ocr_reader.recognition.paddle import BackendUnavailable, PaddleBackend, is_arm_host
from ocr_reader.storage.state import instance_lock


def test_detect_arm_even_when_python_reports_amd64(monkeypatch):
    monkeypatch.setenv("PROCESSOR_IDENTIFIER", "ARMv8 Qualcomm Technologies")
    with patch("platform.machine", return_value="AMD64"), patch("platform.processor", return_value=""):
        assert is_arm_host()
        with pytest.raises(BackendUnavailable):
            PaddleBackend(Settings()).check()


def test_backend_uses_documented_result_contract(tmp_path, monkeypatch):
    raw = {"parsing_res_list": [{"block_label": "text", "block_content": "synthetic contract"}]}

    class Result:
        def save_to_json(self, save_path, ensure_ascii):
            Path(save_path).write_text(json.dumps({"res": raw}), encoding="utf-8")

    class Pipeline:
        def predict(self, input):
            yield Result()

    backend = PaddleBackend(Settings())
    monkeypatch.setattr(backend, "check", lambda: None)
    backend.pipeline = Pipeline()
    assert backend.recognize(tmp_path / "normalized.png", tmp_path / "backend") == raw


def test_lock_prevents_second_instance(tmp_path):
    with instance_lock(tmp_path / "lock"):
        with pytest.raises(RuntimeError):
            with instance_lock(tmp_path / "lock"):
                pass


def test_init_and_empty_check_do_not_require_model(tmp_path, capsys):
    assert main(["--project", str(tmp_path), "init"]) == 0
    assert (tmp_path / "Entrada").is_dir()
    assert main(["--project", str(tmp_path), "check"]) == 0
    assert "Não foi executado OCR" in capsys.readouterr().out


def test_status_does_not_create_database(tmp_path):
    state = tmp_path / "local-state"
    assert main(["--project", str(tmp_path / "project"), "--state-dir", str(state), "status"]) == 0
    assert not state.exists()


def test_configuration_rejects_unimplemented_gpu(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "settings.toml").write_text('[recognition]\ndevice="gpu"', encoding="utf-8")
    assert main(["--project", str(tmp_path), "init"]) == 2

