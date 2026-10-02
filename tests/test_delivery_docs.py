import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def relative_links(path: Path) -> list[Path]:
    content = path.read_text(encoding="utf-8")
    return [
        (path.parent / target).resolve()
        for target in re.findall(r"\]\(([^)#]+)", content)
        if not target.startswith(("http://", "https://"))
    ]


def test_delivery_document_links_exist() -> None:
    for name in ("README.md", "docs/INSTALACION.md", "AI_LOG.md"):
        missing = [str(path) for path in relative_links(ROOT / name) if not path.exists()]
        assert not missing, missing


def test_readme_answers_match_certified_values() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "`057-C` 1.362, `012-B` 1.226" in readme
    assert all(value in readme for value in ("`T015`", "`T023`", "`T038`"))
    assert all(
        value in readme
        for value in ("015-D", "158,216.09", "002-B", "47,595.85", "001-A", "12,663.62")
    )
