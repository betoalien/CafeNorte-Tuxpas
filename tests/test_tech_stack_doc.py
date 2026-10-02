from __future__ import annotations

# ruff: noqa: E501
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/TECH_STACK.md"


def test_tech_stack_links_and_versions_match_repo() -> None:
    text = DOC.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", text):
        assert (DOC.parent / target).resolve().exists(), target

    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = {item.split("==", 1)[0]: item.split("==", 1)[1] for item in pyproject["project"]["dependencies"] if "==" in item}
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    expected = {
        "Pydantic": ("pydantic", dependencies["pydantic"]),
        "Polars": ("polars", dependencies["polars"]),
        "PardoX": ("pardox", dependencies["pardox"]),
        "psycopg": ("psycopg", dependencies["psycopg[binary]"]),
        "ADBC PostgreSQL": ("adbc-driver-postgresql", dependencies["adbc-driver-postgresql"]),
        "dbt-core / dbt-postgres": ("dbt-core", dependencies["dbt-core"]),
    }
    for label, (package, version) in expected.items():
        assert f"{label} | `{version}`" in text
        assert re.search(rf'name = "{re.escape(package)}"\nversion = "{re.escape(version)}"', lock)

    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "superset/Dockerfile").read_text(encoding="utf-8")
    assert "PostgreSQL | `16.4-alpine3.20`" in text
    assert "Redis | `7.2.7-alpine3.21`" in text
    assert "Apache Superset | `4.1.1`" in text
    assert "postgres:16.4-alpine3.20" in compose
    assert "redis:7.2.7-alpine3.21" in compose
    assert "apache/superset:4.1.1" in dockerfile
