import shutil
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg and ffprobe are required",
)


def test_ffmpeg_muxes_local_video_and_audio(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    audio = tmp_path / "audio.m4a"
    output = tmp_path / "merged.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=size=320x180:rate=25", "-t", "1", "-an", str(video)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440", "-t", "1", "-vn", str(audio)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video), "-i", str(audio), "-c", "copy", str(output)],
        check=True,
        capture_output=True,
    )
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert {line.strip() for line in probe.stdout.splitlines()} == {"video", "audio"}

