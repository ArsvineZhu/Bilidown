from __future__ import annotations

import html
import math
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from pathlib import Path


_MAX_XML_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True)
class DanmakuComment:
    start: float
    mode: int
    size: int
    color: int
    text: str


def convert_xml_to_ass(
    source: Path,
    destination: Path,
    *,
    width: int = 1920,
    height: int = 1080,
) -> None:
    if source.stat().st_size > _MAX_XML_BYTES:
        raise ValueError("弹幕 XML 超过 32 MiB，无法安全转换")
    comments = _read_comments(source)
    header = _ass_header(width, height)
    rows = [
        _ass_dialogue(comment, index, width, height)
        for index, comment in enumerate(comments)
    ]
    destination.write_text(header + "\n".join(rows) + "\n", encoding="utf-8-sig")


def _read_comments(source: Path) -> list[DanmakuComment]:
    try:
        root = ElementTree.parse(source).getroot()
    except ElementTree.ParseError as exc:
        raise ValueError("弹幕 XML 格式无效") from exc
    comments: list[DanmakuComment] = []
    for element in root.iter("d"):
        values = (element.get("p") or "").split(",")
        if len(values) < 4:
            continue
        try:
            start = max(0.0, float(values[0]))
            mode = int(values[1])
            size = min(96, max(12, int(values[2])))
            color = min(0xFFFFFF, max(0, int(values[3])))
        except ValueError:
            continue
        text = html.unescape(element.text or "").strip()
        if text:
            comments.append(DanmakuComment(start, mode, size, color, text))
    return comments


def _ass_header(width: int, height: int) -> str:
    return (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "WrapStyle: 2\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Microsoft YaHei,36,&H00FFFFFF,&H00FFFFFF,&H00000000,"
        "&H64000000,0,0,0,0,100,100,0,0,1,1.5,0,7,0,0,0,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
    )


def _ass_dialogue(
    comment: DanmakuComment,
    index: int,
    width: int,
    height: int,
) -> str:
    duration = 8.0
    end = comment.start + duration
    line_height = max(32, comment.size + 6)
    lane_count = max(1, math.floor((height * 0.82) / line_height))
    y = 20 + (index % lane_count) * line_height
    text_width = max(comment.size, len(comment.text) * comment.size)
    if comment.mode == 5:
        position = f"\\an8\\pos({width // 2},{y})"
        end = comment.start + 5.0
    elif comment.mode == 4:
        position = f"\\an2\\pos({width // 2},{height - y})"
        end = comment.start + 5.0
    else:
        position = (
            f"\\move({width + text_width},{y},-{text_width},{y},0,"
            f"{int(duration * 1000)})"
        )
    color = _ass_color(comment.color)
    escaped = _escape_ass(comment.text)
    override = f"{{{position}\\fs{comment.size}\\c{color}}}"
    return (
        f"Dialogue: 0,{_ass_time(comment.start)},{_ass_time(end)},Default,,"
        f"0,0,0,,{override}{escaped}"
    )


def _ass_color(rgb: int) -> str:
    red = (rgb >> 16) & 0xFF
    green = (rgb >> 8) & 0xFF
    blue = rgb & 0xFF
    return f"&H00{blue:02X}{green:02X}{red:02X}&"


def _ass_time(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    whole_seconds, fraction = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{fraction:02d}"


def _escape_ass(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\r\n", "\\N")
        .replace("\n", "\\N")
        .replace("\r", "\\N")
    )
