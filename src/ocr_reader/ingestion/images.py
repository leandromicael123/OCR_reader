from dataclasses import dataclass
from pathlib import Path
import hashlib
import re
import time
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from ocr_reader.config import Settings


EXTENSIONS = {".jpg", ".jpeg", ".png"}


class WaitingForFile(Exception):
    """Ficheiro indisponível ou ainda em alteração; tentar numa execução futura."""


class InvalidImage(Exception):
    pass


@dataclass
class Snapshot:
    sha256: str
    original: Path
    normalized: Path
    width: int
    height: int


def discover(folder: Path) -> list[Path]:
    def natural_key(path: Path):
        return [(1, int(p)) if p.isdigit() else (0, p.casefold())
                for p in re.split(r"(\d+)", path.name)]
    return sorted((p for p in folder.iterdir()
                   if p.suffix.lower() in EXTENSIONS and p.is_file() and not p.is_symlink()),
                  key=natural_key)


def signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def acquire(source: Path, staging: Path, settings: Settings) -> Snapshot:
    """Preserva os bytes originais; imagem de inferência tem EXIF aplicado."""
    try:
        if source.is_symlink():
            raise InvalidImage("Ligações simbólicas não são aceites.")
        previous = signature(source)
        for _ in range(settings.stable_samples - 1):
            time.sleep(settings.stable_interval_seconds)
            current = signature(source)
            if current != previous:
                raise WaitingForFile("Ficheiro ainda está a mudar.")
            previous = current
        if previous[0] == 0:
            raise WaitingForFile("Ficheiro vazio; a cópia pode não ter terminado.")
        if previous[0] > settings.max_file_mb * 1024 * 1024:
            raise InvalidImage("Imagem excede o limite de tamanho configurado.")
        staging.mkdir(parents=True, exist_ok=True)
        original = staging / ("original" + source.suffix.lower())
        # Limite durante a cópia também: a origem pode crescer depois de stat().
        with source.open("rb") as src, original.open("wb") as dst:
            size = 0
            while chunk := src.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_file_mb * 1024 * 1024:
                    raise WaitingForFile("A origem cresceu durante a leitura.")
                dst.write(chunk)
        if signature(source) != previous or original.stat().st_size != previous[0]:
            raise WaitingForFile("Ficheiro alterado durante a cópia.")
    except (PermissionError, FileNotFoundError, OSError) as exc:
        raise WaitingForFile("Ficheiro bloqueado ou indisponível; confirmar sincronização.") from exc

    digest = sha256_file(original)
    normalized = staging / "normalized.png"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(original) as image:
                if image.format not in {"JPEG", "PNG"}:
                    raise InvalidImage("O conteúdo não é JPEG nem PNG.")
                if image.width * image.height > settings.max_pixels:
                    raise InvalidImage("Imagem excede o limite de píxeis.")
                if getattr(image, "n_frames", 1) != 1:
                    raise InvalidImage("Imagens animadas/multipágina não são suportadas.")
                image.verify()
            with Image.open(original) as image:
                image.load()
                upright = ImageOps.exif_transpose(image)
                rgba = upright.convert("RGBA")
                white = Image.new("RGBA", rgba.size, "white")
                white.alpha_composite(rgba)
                white.convert("RGB").save(normalized)
                width, height = upright.size
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise InvalidImage("Não foi possível descodificar integralmente a imagem.") from exc
    return Snapshot(digest, original, normalized, width, height)
