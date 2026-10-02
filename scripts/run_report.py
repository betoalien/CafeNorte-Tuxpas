"""Create the static local run report without changing pipeline state."""
# The HTML template is intentionally kept inline and readable as one document.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import html
import os
import platform
import subprocess
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    report_path = ROOT / "artifacts/reports/run_report.html"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        print(f"Run report dry-run: {report_path}")
        return
    with (
        psycopg.connect(
            host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ.get("PIPELINE_USER", "pipeline"),
            password=os.environ["PIPELINE_PASSWORD"],
        ) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "SELECT run_id, started_at, completed_at FROM audit.run_log ORDER BY started_at DESC LIMIT 1"
        )
        run = cur.fetchone()
        cur.execute(
            "SELECT source_file, load_mode, input_count, accepted_count, rejected_count FROM audit.ingestion_manifest WHERE run_id=%s ORDER BY source_file",
            (run[0],),
        )
        modes = cur.fetchall()
        tables = [
            "pos_sales",
            "inventory_snapshots",
            "ecommerce_orders",
            "exchange_rates",
            "stores",
            "products",
            "sku_mappings",
        ]
        silver = []
        for table in tables:
            cur.execute(f"SELECT count(*) FROM silver.{table}")
            silver.append((f"silver.{table}", cur.fetchone()[0]))
    marts = [
        "mart_inventory_turnover_top10",
        "mart_stockouts_over_3_days",
        "mart_monthly_channel_growth",
        "mart_negative_margin_products",
        "mart_source_reconciliation",
    ]
    gold = []
    with (
        psycopg.connect(
            host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            dbname=os.environ["POSTGRES_DB"],
            user="superset_ro",
            password=os.environ["SUPERSET_RO_PASSWORD"],
        ) as conn,
        conn.cursor() as cur,
    ):
        for table in marts:
            cur.execute(f"SELECT count(*) FROM analytics.{table}")
            gold.append((f"analytics.{table}", cur.fetchone()[0]))
    duration = "n/a"
    if run[1] and run[2]:
        duration = str(run[2] - run[1])
    validate_file = ROOT / "artifacts/reports/last_validate.txt"
    validate = (
        validate_file.read_text().strip() if validate_file.exists() else "No ejecutado todavía"
    )
    rows = "".join(
        f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td><td>{esc(d)}</td><td>{esc(e)}</td></tr>"
        for a, b, c, d, e in modes
    )
    table_rows = "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td></tr>" for a, b in silver + gold)
    answers = [
        ("P1", "057-C, 012-B, 041-D"),
        ("P2", "T015, T023, T038"),
        ("P3", "ONLINE vs tiendas POS"),
        ("P4", "015-D, 002-B, 001-A"),
    ]
    answer_rows = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in answers)
    port = os.environ.get("SUPERSET_PORT", "8088")
    document_links = "<a href='../../README.md'>README</a> · <a href='../../AI_LOG.md'>AI_LOG</a> · <a href='../benchmark.md'>benchmark</a> · <a href='../final-validation.md'>evidencia final</a>"
    content = f"""<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='color-scheme' content='light dark'><title>CaféNorte run report</title><style>body{{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;line-height:1.45}}table{{border-collapse:collapse;width:100%;margin:1rem 0}}td,th{{border:1px solid #888;padding:.45rem;text-align:left}}code{{background:#8883;padding:.1rem .3rem}}a{{color:#1769aa}}@media(prefers-color-scheme:dark){{a{{color:#7cc4ff}}}}</style></head><body><h1>CaféNorte · reporte de corrida</h1><p><b>run_id:</b> <code>{esc(run[0])}</code><br><b>inicio:</b> {esc(run[1])}<br><b>fin:</b> {esc(run[2])}<br><b>duración:</b> {esc(duration)}</p><h2>Fuentes</h2><table><tr><th>Fuente</th><th>Modo</th><th>Input</th><th>Aceptadas</th><th>Rechazadas</th></tr>{rows}</table><h2>Conteos</h2><table>{table_rows}</table><h2>Respuestas</h2><table><tr><th>Pregunta</th><th>Resumen</th></tr>{answer_rows}</table><h2>Validación</h2><pre>{esc(validate)}</pre><h2>Superset</h2><p><a href='http://127.0.0.1:{esc(port)}'>http://127.0.0.1:{esc(port)}</a><br>Usuarios: admin, director, gerente_t001. Contraseñas en <code>.env</code>.</p><p>{document_links}</p></body></html>"""
    report_path.write_text(content, encoding="utf-8")
    print(f"Run report: {report_path}")
    if not args.no_browser and not os.environ.get("CI"):
        if platform.system() == "Darwin" and shutil_which("open"):
            subprocess.run(["open", str(report_path)], check=False)
        elif os.environ.get("WSL_DISTRO_NAME") and shutil_which("wslview"):
            subprocess.run(["wslview", str(report_path)], check=False)
        elif platform.system() == "Linux" and shutil_which("xdg-open"):
            subprocess.run(["xdg-open", str(report_path)], check=False)


def shutil_which(command: str) -> str | None:
    return next(
        (
            str(Path(directory) / command)
            for directory in os.environ.get("PATH", "").split(os.pathsep)
            if (Path(directory) / command).exists()
        ),
        None,
    )


if __name__ == "__main__":
    main()
