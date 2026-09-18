from pathlib import Path
from unittest.mock import patch

from PIL import Image
import pytest

from ocr_reader.config import Settings
from ocr_reader.ingestion.images import acquire, discover, InvalidImage, WaitingForFile


FAST = Settings(stable_interval_seconds=0)


def test_natural_sort_and_extension_filter(tmp_path):
    for name in ["pagina_10.png", "pagina_2.JPG", "pagina_1.jpeg", "other.tmp", "data.json"]:
        (tmp_path / name).touch()
    assert [p.name for p in discover(tmp_path)] == ["pagina_1.jpeg", "pagina_2.JPG", "pagina_10.png"]


def test_detects_changing_file(tmp_path):
    source = tmp_path / "a.png"
    Image.new("RGB", (10, 10)).save(source)
    with patch("ocr_reader.ingestion.images.signature", side_effect=[(100, 1), (101, 2)]):
        with pytest.raises(WaitingForFile):
            acquire(source, tmp_path / "out", FAST)


def test_zero_bytes_waits_instead_of_corruption(tmp_path):
    source = tmp_path / "a.png"
    source.touch()
    with pytest.raises(WaitingForFile):
        acquire(source, tmp_path / "out", FAST)


def test_exif_orientation_and_original_bytes(tmp_path):
    source = tmp_path / "rotated.jpg"
    image = Image.new("RGB", (20, 40), "white")
    exif = Image.Exif()
    exif[274] = 6
    image.save(source, exif=exif)
    snapshot = acquire(source, tmp_path / "out", FAST)
    assert (snapshot.width, snapshot.height) == (40, 20)
    assert snapshot.original.read_bytes() == source.read_bytes()


def test_pixel_limit_before_full_decode(tmp_path):
    source = tmp_path / "a.png"
    Image.new("RGB", (100, 100)).save(source)
    with pytest.raises(InvalidImage):
        acquire(source, tmp_path / "out", Settings(stable_interval_seconds=0, max_pixels=50))


def test_disguised_format_rejected(tmp_path):
    source = tmp_path / "fake.png"
    Image.new("RGB", (20, 20)).save(source, format="BMP")
    with pytest.raises(InvalidImage):
        acquire(source, tmp_path / "out", FAST)

