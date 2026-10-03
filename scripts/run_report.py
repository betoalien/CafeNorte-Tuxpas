"""Generate the local, self-contained run report from PostgreSQL."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import os
import platform
import re
import subprocess
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datos"
SILVER_TABLES = [
    "pos_sales",
    "inventory_snapshots",
    "ecommerce_orders",
    "exchange_rates",
    "stores",
    "products",
    "sku_mappings",
]
GOLD_TABLES = [
    "mart_inventory_turnover_top10",
    "mart_inventory_turnover_by_store",
    "mart_stockouts_over_3_days",
    "mart_monthly_channel_growth",
    "mart_negative_margin_products",
    "mart_source_reconciliation",
]

LAST_SUCCESSFUL_RUN_SQL = (
    "SELECT run_id, started_at, completed_at FROM audit.run_log "
    "WHERE status IN ('succeeded','success','completed') "
    "ORDER BY started_at DESC LIMIT 1"
)
MANIFEST_SQL = (
    "SELECT source_file, load_mode, input_count, accepted_count, rejected_count, "
    "sha256_after, completed_at FROM audit.ingestion_manifest "
    "WHERE run_id=%s ORDER BY source_file"
)
LAST_RUN_SQL = (
    "SELECT run_id, started_at, completed_at, status, load_mode "
    "FROM audit.run_log ORDER BY started_at DESC LIMIT 1"
)
P1_SQL = (
    "SELECT product_id, inventory_turnover_ratio "
    "FROM analytics.mart_inventory_turnover_top10 ORDER BY ranking LIMIT 3"
)
P2_SQL = (
    "SELECT tienda_id, product_id, start_date, end_date, days "
    "FROM analytics.mart_stockouts_over_3_days ORDER BY tienda_id, start_date"
)
ONLINE_SQL = (
    "SELECT month_start, mom_growth_pct FROM analytics.mart_monthly_channel_growth "
    "WHERE channel='ONLINE' ORDER BY month_start DESC LIMIT 1"
)
HIGHEST_MOM_SQL = (
    "SELECT channel, mom_growth_pct FROM analytics.mart_monthly_channel_growth "
    "WHERE mom_growth_pct IS NOT NULL ORDER BY mom_growth_pct DESC LIMIT 1"
)
LOWEST_MOM_SQL = (
    "SELECT channel, mom_growth_pct FROM analytics.mart_monthly_channel_growth "
    "WHERE mom_growth_pct IS NOT NULL ORDER BY mom_growth_pct LIMIT 1"
)
P3_SUMMARY_SQL = (
    "SELECT channel_type, sum(sales_mxn), "
    "sum(sales_mxn) FILTER (WHERE month_start = DATE '2025-04-01'), "
    "sum(sales_mxn) FILTER (WHERE month_start = DATE '2026-03-01') "
    "FROM analytics.mart_monthly_channel_type_growth "
    "GROUP BY channel_type ORDER BY channel_type"
)
P4_SQL = (
    "SELECT product_id, round(sum(gross_margin_mxn), 2) "
    "FROM analytics.mart_negative_margin_products "
    "GROUP BY product_id ORDER BY sum(gross_margin_mxn)"
)


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def dotenv() -> dict[str, str]:
    path = ROOT / ".env"
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"').strip("'")
    return values


def env(name: str, default: str = "") -> str:
    return os.environ.get(name) or dotenv().get(name, default)


def conn_kwargs(user: str, password_name: str) -> dict[str, object]:
    return {
        "host": env("POSTGRES_HOST", "127.0.0.1"),
        "port": int(env("POSTGRES_PORT", "5432")),
        "dbname": env("POSTGRES_DB", "cafenorte"),
        "user": user,
        "password": env(password_name),
    }


def local_time(value: object) -> str:
    if not isinstance(value, dt.datetime):
        return "sin fecha"
    current = (
        value.astimezone() if value.tzinfo else value.replace(tzinfo=dt.UTC).astimezone()
    )
    return current.strftime("%Y-%m-%d %H:%M:%S %Z")


def short(value: object) -> str:
    return str(value).replace("-", "")[:8]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def original_hashes() -> dict[str, str]:
    expected: dict[str, str] = {}
    sums = DATA / "SHA256SUMS"
    if sums.exists():
        for line in sums.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^([0-9a-fA-F]{64})\s+(.+)$", line)
            if match:
                expected[Path(match.group(2)).name] = match.group(1).lower()
    return expected


def platform_label() -> str:
    system, machine = platform.system(), platform.machine()
    if system == "Darwin" and machine == "arm64":
        return "soportado (probado)"
    if system == "Darwin" and machine == "x86_64":
        return "no verificado (Intel)"
    if system == "Linux" and machine in {"x86_64", "amd64"}:
        return "soportado"
    return "no disponible"


def fmt_number(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (int, float)) or value.__class__.__name__ == "Decimal":
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return esc(value)


def fmt_pct(value: object) -> str:
    return f"{value:+.1f}%".replace("-", "\u2212")


def p3_summary(
    physical: tuple[object, object, object],
    ecommerce: tuple[object, object, object],
    online: tuple[object, object],
    highest: tuple[object, object],
    lowest: tuple[object, object],
) -> str:
    physical_mom = physical[2] / physical[1] - 1
    ecommerce_mom = ecommerce[2] / ecommerce[1] - 1
    total_sales = physical[0] + ecommerce[0]
    return (
        f"Físico {fmt_number(physical[0] / 1_000_000)} M MXN "
        f"({fmt_pct(physical_mom * 100)} abr→mar); "
        f"e-commerce {fmt_number(ecommerce[0] / 1_000_000)} M MXN "
        f"({fmt_pct(ecommerce_mom * 100)}); "
        f"e-commerce = {ecommerce[0] / total_sales * 100:.1f}% de las ventas. "
        f"Detalle por canal, último mes: ONLINE {fmt_pct(online[1])} ({online[0]}); "
        f"mayor {highest[0]} {fmt_pct(highest[1])}; menor {lowest[0]} {fmt_pct(lowest[1])}"
    )


def source_rows(
    cur: psycopg.Cursor, current_run: tuple, force_mode: str | None
) -> tuple[list[tuple], str]:
    cur.execute(LAST_SUCCESSFUL_RUN_SQL)
    successful = cur.fetchone() or current_run
    skipped = force_mode == "skipped" or (current_run and str(current_run[0]) != str(successful[0]))
    manifest_run = successful[0] if skipped else current_run[0]
    cur.execute(MANIFEST_SQL, (manifest_run,))
    records = {Path(str(row[0])).name: row for row in cur.fetchall()}
    expected = original_hashes()
    rows = []
    for filename in (
        "sales.csv",
        "inventory.json",
        "ecommerce_orders.parquet",
        "exchange_rates.csv",
    ):
        row = records.get(filename)
        if row is None:
            continue
        _source_file, mode, input_count, accepted, rejected, digest, completed = row
        path = DATA / filename
        actual = sha256(path) if path.exists() else ""
        verified = bool(expected.get(filename) and actual == expected[filename])
        rows.append(
            (
                filename,
                "sin cambios" if skipped else mode,
                input_count,
                accepted,
                rejected,
                digest,
                completed,
                verified,
            )
        )
    summary = (
        (
            "Corrida skipped: las 4 fuentes no cambiaron desde "
            f"{short(successful[0])} ({local_time(successful[2])})"
        )
        if skipped
        else ""
    )
    return rows, summary


def query_answers() -> dict[str, str]:
    answers: dict[str, str] = {}
    with (
        psycopg.connect(**conn_kwargs("superset_ro", "SUPERSET_RO_PASSWORD")) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(P1_SQL)
        answers["P1"] = "; ".join(
            f"{product}: {fmt_number(ratio)}x" for product, ratio in cur.fetchall()
        )
        cur.execute(P2_SQL)
        answers["P2"] = (
            "; ".join(
                f"{store} / {product}: {start}—{end} ({days} días)"
                for store, product, start, end, days in cur.fetchall()
            )
            or "Sin rachas certificadas"
        )
        cur.execute(ONLINE_SQL)
        online = cur.fetchone()
        cur.execute(HIGHEST_MOM_SQL)
        highest = cur.fetchone()
        cur.execute(LOWEST_MOM_SQL)
        lowest = cur.fetchone()
        cur.execute(P3_SUMMARY_SQL)
        p3_totals = {row[0]: row[1:] for row in cur.fetchall()}
        physical, ecommerce = p3_totals["FISICO"], p3_totals["ECOMMERCE"]
        answers["P3"] = p3_summary(
            physical, ecommerce, online, highest, lowest
        )
        cur.execute(P4_SQL)
        answers["P4"] = "; ".join(
            f"{product}: {fmt_number(margin)} MXN" for product, margin in cur.fetchall()
        )
    return answers


def hidden_credentials() -> str:
    values = [
        ("admin", env("SUPERSET_ADMIN_PASSWORD"), "Administración"),
        ("director", env("DIRECTOR_PASSWORD"), "Toda la red, incluido ONLINE"),
        ("gerente_t001", env("GERENTE_T001_PASSWORD"), "4 respuestas de T001"),
    ]
    rows = "".join(
        "<tr><td>"
        + esc(user)
        + "</td><td>"
        + esc(role)
        + "</td><td><span class='secret' data-secret='"
        + esc(password)
        + "'>••••••••</span> <button type='button' "
        + "onclick='showSecret(this)'>Mostrar</button> <button type='button' "
        + "onclick='copySecret(this)'>Copiar</button></td></tr>"
        for user, password, role in values
    )
    return (
        "<div id='credentials'><p><b>Credenciales locales de demostración, "
        "generadas para esta instalación.</b></p><table><tr><th>Usuario</th>"
        "<th>Rol</th><th>Contraseña</th></tr>"
        + rows
        + "</table></div>"
    )


def render_source_row(source: tuple) -> str:
    name, source_mode, input_count, accepted, rejected, digest, completed, verified = source
    return (
        "<tr><td>"
        + esc(name)
        + "</td><td>"
        + esc(source_mode)
        + f"</td><td>{input_count:,}</td><td>{accepted:,}</td>"
        + f"<td>{rejected:,}</td><td>{esc(str(digest)[:12])}</td>"
        + f"<td>{'original del cliente ✓' if verified else 'no verificado'}</td>"
        + f"<td>{local_time(completed)}</td></tr>"
    )
def render(force_mode: str | None = None) -> str:
    with (
        psycopg.connect(
            **conn_kwargs(env("PIPELINE_USER", "pipeline"), "PIPELINE_PASSWORD")
        ) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(LAST_RUN_SQL)
        run = cur.fetchone()
        if not run:
            raise RuntimeError("No existe una corrida en audit.run_log")
        sources, summary = source_rows(cur, run[:3], force_mode)
        silver = []
        for table in SILVER_TABLES:
            cur.execute(f"SELECT count(*) FROM silver.{table}")
            silver.append((f"silver.{table}", cur.fetchone()[0]))
    with (
        psycopg.connect(**conn_kwargs("superset_ro", "SUPERSET_RO_PASSWORD")) as conn,
        conn.cursor() as cur,
    ):
        gold = []
        for table in GOLD_TABLES:
            cur.execute(f"SELECT count(*) FROM analytics.{table}")
            gold.append((f"analytics.{table}", cur.fetchone()[0]))
    validate_file = ROOT / "artifacts/reports/last_validate.txt"
    validate = (
        validate_file.read_text(encoding="utf-8").strip()
        if validate_file.exists()
        else "sin corridas"
    )
    validate_status = "PASS" if "PASS" in validate else "FAIL"
    duration = (run[2] - run[1]).total_seconds() if run[1] and run[2] else 0.0
    answers = query_answers()
    source_html = "".join(render_source_row(source) for source in sources)
    rows = "".join(f"<tr><td>{esc(name)}</td><td>{count:,}</td></tr>" for name, count in silver)
    gold_rows = "".join(
        f"<tr><td>{esc(name)}</td><td>{count:,}</td></tr>" for name, count in gold
    )
    answer_rows = "".join(
        f"<tr><th>{key}</th><td>{esc(value)}</td></tr>" for key, value in answers.items()
    )
    port = env("SUPERSET_PORT")
    dashboard_url = f"http://127.0.0.1:{port}/superset/dashboard/cafenorte-4-respuestas/"
    store_dashboard_url = f"http://127.0.0.1:{port}/superset/dashboard/cafenorte-mi-tienda/"
    mode = "skipped" if force_mode == "skipped" else ("full" if force_mode == "full" else run[4])
    links = (
        "<a href='../evidence/benchmark.md'>benchmark</a> · "
        "<a href='../evidence/final-validation.md'>validación final</a> · "
        "<a href='../../README.md'>README</a> · "
        "<a href='../../AI_LOG.md'>AI_LOG</a>"
    )
    summary_html = f"<p class='summary'>{esc(summary)}</p>" if summary else ""
    return (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        "<meta name='color-scheme' content='light dark'>"
        "<title>CaféNorte · reporte de corrida</title>"
        "<style>body{font:15px system-ui,sans-serif;max-width:1200px;"
        "margin:2rem auto;padding:0 1rem;line-height:1.45}"
        "table{border-collapse:collapse;width:100%;margin:1rem 0}"
        "td,th{border:1px solid #888;padding:.45rem;text-align:left}th{background:#8882}"
        "code{background:#8883;padding:.1rem .3rem}a{color:#1769aa}button{margin-left:.25rem}"
        ".summary{padding:.7rem;border-left:4px solid #1769aa}.state{font-size:1.1rem}"
        "@media(prefers-color-scheme:dark){a{color:#7cc4ff}}</style>"
        "<script>function showSecret(b){const s=b.parentElement.querySelector('.secret');"
        "const shown=s.dataset.shown==='1';s.textContent=shown?'••••••••':s.dataset.secret;"
        "s.dataset.shown=shown?'0':'1';b.textContent=shown?'Mostrar':'Ocultar'}"
        "function copySecret(b){navigator.clipboard.writeText("
        "b.parentElement.querySelector('.secret').dataset.secret)}"
        "</script></head><body><h1>CaféNorte · reporte de corrida</h1>"
        f"{summary_html}<p class='state'><b>Estado:</b> carga <code>{esc(mode)}</code> · "
        f"validate <b>{validate_status}</b> ({esc(local_time(dt.datetime.now(dt.UTC)))}) · "
        f"PardoX: {esc(platform_label())}</p>"
        f"<p><b>run_id:</b> <code>{esc(run[0])}</code><br>"
        f"<b>inicio:</b> {esc(local_time(run[1]))}<br>"
        f"<b>fin:</b> {esc(local_time(run[2]))}<br>"
        f"<b>duración:</b> {duration:.2f} s</p>"
        "<h2>Fuentes</h2><table><tr><th>Fuente</th><th>Modo</th><th>Input</th>"
        "<th>Aceptadas</th><th>Rechazadas</th><th>SHA-256</th><th>Verificación</th>"
        f"<th>Carga</th></tr>{source_html}</table>"
        "<h2>Silver</h2><table><tr><th>Tabla</th><th>Filas</th></tr>"
        f"{rows}</table><h2>Gold (analytics)</h2><table><tr><th>Tabla</th><th>Filas</th></tr>"
        f"{gold_rows}</table><h2>Respuestas</h2><table>{answer_rows}</table>"
        "<h2>Superset listo</h2><p>"
        f"<b>Dirección</b>: <a href='{esc(dashboard_url)}'>{esc(dashboard_url)}</a><br>"
        f"<b>Mi tienda</b>: <a href='{esc(store_dashboard_url)}'>{esc(store_dashboard_url)}</a><br>"
        "<b>director</b>: las 4 respuestas de toda la red<br>"
        "<b>gerente_t001</b>: las 4 respuestas solo de T001<br>"
        f"<b>admin</b>: solo administración</p>{hidden_credentials()}"
        f"<h2>Validación</h2><pre>{esc(validate)}</pre><p>{links}</p></body></html>"
    )


def open_report(path: Path, no_browser: bool) -> None:
    if no_browser or os.environ.get("CI"):
        return
    command = (
        "open"
        if platform.system() == "Darwin"
        else "wslview"
        if os.environ.get("WSL_DISTRO_NAME")
        else "xdg-open"
        if platform.system() == "Linux"
        else None
    )
    if command and shutil_which(command):
        subprocess.run([command, str(path)], check=False)


def shutil_which(command: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.exists():
            return str(candidate)
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mode", choices=("skipped", "full"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    report_path = ROOT / "artifacts/reports/run_report.html"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        print(f"Run report dry-run: {report_path}")
        return
    report_path.write_text(render(args.mode), encoding="utf-8")
    report_path.chmod(0o600)
    print(f"Run report: {report_path}")
    open_report(report_path, args.no_browser)


if __name__ == "__main__":
    main()
