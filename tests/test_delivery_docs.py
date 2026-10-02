import csv
import re
from decimal import Decimal
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
    for name in ("README.md", "docs/CONFIGURACION.md", "docs/PARDOX.md", "AI_LOG.md"):
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
    assert "Físico 20.72 M MXN (+2.7% abr→mar)" in readme
    assert f"e-commerce 4.23 M MXN ({chr(0x2212)}8.5%)" in readme
    assert "e-commerce = 16.9%" in readme


def test_readme_p3_figures_match_certified_csv() -> None:
    rows = list(
        csv.DictReader(
            (ROOT / "artifacts/evidence/answers/p3_monthly_channel_type_growth.csv").open()
        )
    )
    totals = {
        channel: sum(Decimal(row["sales_mxn"]) for row in rows if row["channel_type"] == channel)
        for channel in ("FISICO", "ECOMMERCE")
    }
    assert totals["FISICO"].quantize(Decimal("0.01")) == Decimal("20721035.50")
    assert totals["ECOMMERCE"].quantize(Decimal("0.01")) == Decimal("4228882.71")
    assert len([row for row in rows if row["channel_type"] == "FISICO"]) == 12
    assert len([row for row in rows if row["channel_type"] == "ECOMMERCE"]) == 12
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "20.72 M MXN" in readme and "4.23 M MXN" in readme


def test_production_services_match_aws_proposal() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    proposal = (ROOT / "docs/PROPUESTA_AWS.md").read_text(encoding="utf-8")
    production = readme.split("## Llevarlo a producción", 1)[1].split("## ", 1)[0]
    for service in (
        "S3", "Lambda", "ECS/Fargate", "Glue", "Athena", "dbt", "Superset",
        "Lightsail", "Secrets Manager", "CloudWatch", "CloudTrail",
    ):
        assert service in production
        assert service in proposal
    assert "RDS" not in production
    assert "ElastiCache" not in production
