from pathlib import Path

import pytest

from bilidown.files import ensure_output_directory, move_without_overwrite, sanitize_filename


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ('a<b>:c"d/e\\f|g?h*', "a_b__c_d_e_f_g_h_"),
        ("CON", "_CON"),
        ("  a   b. ", "a b"),
    ],
)
def test_sanitize_filename(value: str, expected: str) -> None:
    assert sanitize_filename(value) == expected


def test_requires_absolute_output_path() -> None:
    with pytest.raises(ValueError, match="绝对路径"):
        ensure_output_directory("relative/path")


def test_move_without_overwrite(tmp_path: Path) -> None:
    destination = tmp_path / "out"
    destination.mkdir()
    (destination / "video.mp4").write_bytes(b"old")
    source = tmp_path / "video.mp4"
    source.write_bytes(b"new")
    moved = move_without_overwrite(source, destination)
    assert moved.name == "video (1).mp4"
    assert moved.read_bytes() == b"new"

