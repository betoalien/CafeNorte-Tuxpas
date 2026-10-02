from __future__ import annotations

import html
import importlib.util
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import psycopg

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("run_report", ROOT / "scripts/run_report.py")
assert _SPEC and _SPEC.loader
run_report = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(run_report)


def _assert_report(content: str) -> None:
    assert content.count("<tr><td>") >= 4
    for href in re.findall(r"href=['\"]([^'\"]+)['\"]", content):
        if urlparse(href).scheme:
            continue
        assert (ROOT / "artifacts/reports" / href).resolve().exists(), href
    secrets = [
        os.environ.get(name, "")
        for name in ("SUPERSET_ADMIN_PASSWORD", "DIRECTOR_PASSWORD", "GERENTE_T001_PASSWORD")
    ]
    hidden = content.split("<div id='credentials'>", 1)[1].split("</div>", 1)[0]
    visible = content.replace(hidden, "")
    for secret in secrets:
        if secret:
            assert secret not in visible
    with (
        psycopg.connect(**run_report.conn_kwargs("superset_ro", "SUPERSET_RO_PASSWORD")) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "SELECT product_id, round(sum(gross_margin_mxn), 2) "
            "FROM analytics.mart_negative_margin_products "
            "GROUP BY product_id ORDER BY sum(gross_margin_mxn)"
        )
        for product, margin in cur.fetchall():
            assert html.escape(str(product)) in content
            assert f"{margin:,.2f}".rstrip("0").rstrip(".") in content


def test_report_skipped_and_full(tmp_path: Path) -> None:
    for mode in ("skipped", "full"):
        content = run_report.render(mode)
        (tmp_path / f"{mode}.html").write_text(content, encoding="utf-8")
        _assert_report(content)
