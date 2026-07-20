import json
import re
import tomllib
from pathlib import Path
from urllib.parse import unquote

import yaml

import bilidown


ROOT = Path(__file__).parents[1]
EXCLUDED_PARTS = {".git", ".tools", ".venv", "build", "dist", "node_modules", "output"}
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")


def markdown_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*.md")
        if not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts)
    ]


def test_internal_markdown_links_exist() -> None:
    missing: list[str] = []
    for document in markdown_files():
        for target in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
            target = target.strip().strip("<>").split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (document.parent / unquote(target)).resolve()
            if not resolved.exists():
                missing.append(f"{document.relative_to(ROOT)} -> {target}")
    assert not missing, "Missing documentation targets:\n" + "\n".join(missing)


def test_documentation_entrypoints_and_sections_exist() -> None:
    required = {
        "README.md": ["## 五分钟开始", "## 文档导航"],
        "docs/README.md": ["## Level 0", "## Level 1", "## Level 2", "## Level 3", "## Developer"],
        "CONTRIBUTING.md": ["## Commit 与 Pull Request"],
        "SECURITY.md": ["## 私密报告"],
    }
    for relative, headings in required.items():
        content = (ROOT / relative).read_text(encoding="utf-8")
        for heading in headings:
            assert heading in content, f"{relative} is missing {heading}"


def test_agents_guide_has_required_title_and_length() -> None:
    content = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert content.startswith("# Repository Guidelines\n")
    words = re.findall(r"\b[A-Za-z0-9][A-Za-z0-9'./+-]*\b", content)
    assert 200 <= len(words) <= 500, f"AGENTS.md has {len(words)} words"


def test_project_versions_match() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    cargo = tomllib.loads(
        (ROOT / "src-tauri" / "Cargo.toml").read_text(encoding="utf-8")
    )
    tauri = json.loads(
        (ROOT / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8")
    )
    frontend = json.loads(
        (ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    assert project["project"]["version"] == bilidown.__version__
    assert cargo["package"]["version"] == bilidown.__version__
    assert tauri["version"] == bilidown.__version__
    assert frontend["version"] == bilidown.__version__


def test_application_authorship_matches_bundle_metadata() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    cargo = tomllib.loads(
        (ROOT / "src-tauri" / "Cargo.toml").read_text(encoding="utf-8")
    )
    tauri = json.loads(
        (ROOT / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8")
    )
    assert project["project"]["authors"] == [
        {"name": "Arsvine Zhu"},
        {"name": "Hackintosh_HD"},
    ]
    assert cargo["package"]["authors"] == ["Arsvine Zhu", "Hackintosh_HD"]
    assert tauri["bundle"]["publisher"] == "Arsvine Zhu"
    assert tauri["bundle"]["copyright"] == "Copyright © 2026 Arsvine Zhu"


def test_windows_portable_build_contract() -> None:
    script = (ROOT / "packaging" / "build-portable.ps1").read_text(encoding="utf-8")
    readme = (ROOT / "packaging" / "PORTABLE_README_zh-CN.txt").read_text(
        encoding="utf-8"
    )
    assert '"Bilidown-$version-windows-x64"' in script
    assert "$portableName-portable.zip" in script
    for entry in (
        "Bilidown.exe",
        "bilidown-backend.exe",
        "README.txt",
        "SHA256SUMS.txt",
        "THIRD_PARTY_NOTICES.txt",
        "FFMPEG_SOURCE.txt",
    ):
        assert entry in script
    assert "WebView2 Runtime" in readme


def test_github_workflows_are_valid_yaml() -> None:
    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    assert {path.name for path in workflows} == {"ci.yml", "portable.yml"}
    for workflow in workflows:
        parsed = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict)
        assert "jobs" in parsed
