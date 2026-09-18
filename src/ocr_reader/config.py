from dataclasses import dataclass
from pathlib import Path
import hashlib
import os
import tomllib


FOLDERS = ("Entrada", "Resultado", "Processados", "ParaRever", "Erros", "logs")


@dataclass(frozen=True)
class Settings:
    stable_samples: int = 3
    stable_interval_seconds: float = 1.0
    max_file_mb: int = 30
    max_pixels: int = 40_000_000
    pipeline_version: str = "v1.6"
    device: str = "cpu"
    use_doc_orientation_classify: bool = False
    use_doc_unwarping: bool = False

    @classmethod
    def load(cls, project: Path) -> "Settings":
        path = project / "config" / "settings.toml"
        if not path.is_file():
            return cls()
        with path.open("rb") as f:
            config = tomllib.load(f)
        if set(config) - {"input", "recognition"}:
            raise ValueError("Secção desconhecida em config/settings.toml.")
        values = {**config.get("input", {}), **config.get("recognition", {})}
        settings = cls(**values)
        if not 2 <= settings.stable_samples <= 20:
            raise ValueError("stable_samples deve estar entre 2 e 20.")
        if not 0 <= settings.stable_interval_seconds <= 60:
            raise ValueError("Intervalo de estabilidade inválido.")
        if not 1 <= settings.max_file_mb <= 200 or not 1 <= settings.max_pixels <= 100_000_000:
            raise ValueError("Limite de imagem inválido.")
        if settings.device != "cpu":
            raise ValueError("Este protótipo suporta apenas device='cpu'.")
        if settings.use_doc_orientation_classify or settings.use_doc_unwarping:
            raise ValueError("Retificação do modelo ainda não suportada: mudaria as coordenadas dos recortes.")
        if settings.pipeline_version != "v1.6":
            raise ValueError("Adaptador preparado para pipeline_version='v1.6'.")
        return settings


def initialize(project: Path) -> None:
    for name in FOLDERS:
        directory = project / name
        if directory.is_symlink():
            raise ValueError(f"A pasta {name} não pode ser uma ligação simbólica.")
        directory.mkdir(parents=True, exist_ok=True)


def state_directory(project: Path) -> Path:
    """SQLite fora do projeto/OneDrive; identidade separada para cada instalação."""
    key = hashlib.sha256(str(project.resolve()).encode()).hexdigest()[:16]
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "state")))
    return base / "OCR_reader" / key

