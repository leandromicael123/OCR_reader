from importlib import metadata, util
from pathlib import Path
import json
import os
import platform

from ocr_reader.config import Settings


class BackendUnavailable(RuntimeError):
    pass


def is_arm_host() -> bool:
    # platform.machine() pode devolver AMD64 num Python x64 emulado em ARM.
    info = " ".join((platform.machine(), platform.processor(),
                     os.environ.get("PROCESSOR_IDENTIFIER", ""),
                     os.environ.get("PROCESSOR_ARCHITEW6432", ""))).lower()
    return "arm" in info or "aarch64" in info or "qualcomm" in info


def diagnostics() -> dict:
    packages = {}
    for distribution in ("Pillow", "paddlepaddle", "paddleocr"):
        try:
            packages[distribution] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            packages[distribution] = None
    arm = is_arm_host()
    ready = not arm and all(packages.values())
    return {"python": platform.python_version(), "machine": platform.machine(),
            "processor": platform.processor(), "arm_host": arm,
            "packages": packages, "ready_to_try_ocr": ready,
            "note": "Diagnóstico sem carregar modelo; não comprova a execução da inferência."}


class PaddleBackend:
    name = "paddleocr-vl"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.pipeline = None

    def check(self) -> None:
        if is_arm_host():
            raise BackendUnavailable(
                "Este computador é ARM/Qualcomm (mesmo com Python x64 emulado). "
                "O perfil inicial é Intel/AMD x64 CPU. Execute o OCR no computador Intel com 32 GB.")
        if util.find_spec("paddle") is None or util.find_spec("paddleocr") is None:
            raise BackendUnavailable(
                "Motor não instalado. No computador Intel execute scripts/install.ps1 -WithOCR.")

    @property
    def fingerprint(self) -> str:
        versions = diagnostics()["packages"]
        return f"{self.name}:{self.settings.pipeline_version}:cpu:{versions['paddleocr']}:{versions['paddlepaddle']}:adapter-1"

    def recognize(self, image: Path, output: Path) -> dict:
        self.check()
        if self.pipeline is None:
            from paddleocr import PaddleOCRVL
            self.pipeline = PaddleOCRVL(
                pipeline_version=self.settings.pipeline_version, device="cpu",
                use_doc_orientation_classify=False, use_doc_unwarping=False)
        results = iter(self.pipeline.predict(input=str(image)))
        result = next(results, None)
        if result is None:
            raise ValueError("O motor não devolveu resultado.")
        # Cada input é uma única imagem. Várias páginas seriam um erro de contrato.
        if next(results, None) is not None:
            raise ValueError("O motor devolveu várias páginas para uma única imagem.")
        output.mkdir(parents=True, exist_ok=True)
        path = output / "paddle-result.json"
        result.save_to_json(save_path=str(path), ensure_ascii=False)
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw = payload.get("res", payload)
        if not isinstance(raw, dict) or not isinstance(raw.get("parsing_res_list"), list):
            raise ValueError("Formato PaddleOCR inesperado: falta parsing_res_list.")
        return raw

