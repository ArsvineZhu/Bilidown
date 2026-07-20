from pathlib import Path

from bilidown.danmaku import convert_xml_to_ass


def test_converts_scrolling_and_fixed_danmaku_to_ass(tmp_path: Path) -> None:
    source = tmp_path / "comments.xml"
    source.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<i><d p="1.25,1,36,16711680,0,0,0,0">滚动{测试}</d>'
        '<d p="2,5,42,255,0,0,0,0">顶部</d></i>',
        encoding="utf-8",
    )
    destination = tmp_path / "comments.ass"

    convert_xml_to_ass(source, destination)

    output = destination.read_text(encoding="utf-8-sig")
    assert "PlayResX: 1920" in output
    assert "\\move(" in output
    assert "\\an8\\pos(" in output
    assert "&H000000FF&" in output
    assert "滚动\\{测试\\}" in output
    assert "0:00:01.25" in output


def test_rejects_invalid_danmaku_xml(tmp_path: Path) -> None:
    source = tmp_path / "invalid.xml"
    source.write_text("<i>", encoding="utf-8")

    try:
        convert_xml_to_ass(source, tmp_path / "invalid.ass")
    except ValueError as exc:
        assert "XML" in str(exc)
    else:
        raise AssertionError("invalid XML must be rejected")
