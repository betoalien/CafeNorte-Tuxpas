"""SPEC-003 benchmark: equal work, isolated subprocesses, and sanity guards."""

import json
import os
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from .engines import pardox_engine, polars_engine
from .engines.pos_sales import build_pos_sales_pardox, build_pos_sales_polars
from .ingest import DATA, ROOT


def worker(engine: str, result_path: Path) -> None:
    started = time.perf_counter()
    report = pardox_engine.prepare(DATA) if engine == "pardox" else polars_engine.prepare(DATA)
    build = build_pos_sales_pardox if engine == "pardox" else build_pos_sales_polars
    before = time.perf_counter()
    rows = build(DATA / "sales.csv", __import__("uuid").uuid4(), datetime.now(UTC))
    transform_seconds = time.perf_counter() - before
    before = time.perf_counter()
    from .ingest import connect

    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "CREATE TEMP TABLE benchmark_pos_sales (venta_id text, fecha_hora_original text, "
            "fecha_hora_normalizada timestamp, tienda_id text, sku text, product_number text, "
            "cantidad bigint, monto numeric(18,2), moneda text, tipo_comprobante text, "
            "run_id uuid, ingested_at timestamptz, row_hash text)"
        )
        cur.executemany(
            "INSERT INTO benchmark_pos_sales VALUES (" + ",".join(["%s"] * 13) + ")", rows
        )
    load_seconds = time.perf_counter() - before
    report.stage_seconds["all"]["transform"] = transform_seconds
    report.stage_seconds["all"]["load"] = load_seconds
    report.stage_seconds["all"]["total"] = time.perf_counter() - started
    records = []
    for stage, seconds in report.stage_seconds["all"].items():
        records.append(
            {
                "engine": engine,
                "source": "all",
                "stage": stage,
                "seconds": seconds,
                "peak_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                "rows_processed": sum(report.source_rows.values()),
                "source_rows": report.source_rows,
                "engine_fallback": report.fallbacks,
                "python": platform.python_version(),
                "polars": __import__("polars").__version__,
                "pardox": report.versions.get("pardox", "n/a"),
                "cpu": platform.machine(),
                "cold": os.environ.get("CAFENORTE_BENCHMARK_COLD") == "1",
                "output_bytes": report.output_bytes,
                "output_format": "prdx" if engine == "pardox" else "csv",
            }
        )
    records.append(
        {"engine": engine, "stage": "process_total", "seconds": time.perf_counter() - started}
    )
    result_path.write_text(json.dumps(records), encoding="utf-8")


def run_subprocess(engine: str, cold: bool) -> list[dict]:
    with tempfile.NamedTemporaryFile(suffix=".json") as result:
        env = {**os.environ, "CAFENORTE_BENCHMARK_COLD": "1" if cold else "0"}
        subprocess.run(
            [sys.executable, "-m", "cafenorte.benchmark", "--worker", engine, result.name],
            check=True,
            env=env,
            stdout=subprocess.DEVNULL,
        )
        return json.loads(Path(result.name).read_text(encoding="utf-8"))


def main() -> None:
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        worker(sys.argv[2], Path(sys.argv[3]))
        return
    records: list[dict] = []
    for index in range(6):
        engines = ("polars", "pardox") if index % 2 == 0 else ("pardox", "polars")
        for engine in engines:
            records.extend(run_subprocess(engine, cold=index == 0))
    expected = {"sales": 86490, "ecommerce_orders": 9947, "exchange_rates": 730}
    for record in records:
        for source, expected_rows in expected.items():
            if (
                source in record.get("source_rows", {})
                and record["source_rows"][source] != expected_rows
            ):
                raise RuntimeError(f"Benchmark row guard failed: {record}")
        if record.get("stage") in {
            "read",
            "validate",
            "transform",
            "load",
            "total",
            "to_prdx",
        } and (record["rows_processed"] <= 0 or record["seconds"] < 0.001):
            raise RuntimeError(f"Benchmark sanity guard failed: {record}")
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    (logs / f"benchmark_{stamp}.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )
    lines = [
        "# Benchmark PardoX vs Polars",
        "",
        "| Engine | Stage | Median s | Min s | Difference vs Polars | Peak MB |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for stage in ("read", "validate", "transform", "load", "to_prdx", "total"):
        medians = {}
        for engine in ("polars", "pardox"):
            values = [
                r["seconds"]
                for r in records
                if r.get("engine") == engine and r.get("stage") == stage
            ]
            if not values:
                continue
            medians[engine] = statistics.median(values)
            difference = (medians[engine] / medians.get("polars", medians[engine]) - 1) * 100
            peak = max(
                r["peak_mb"]
                for r in records
                if r.get("engine") == engine and r.get("stage") == stage
            )
            lines.append(
                f"| {engine} | {stage} | {medians[engine]:.6f} | {min(values):.6f} | "
                f"{difference:+.1f}% | {peak:.1f} |"
            )
    polars_size = max(
        r["output_bytes"] for r in records if r.get("engine") == "polars" and "output_bytes" in r
    )
    pardox_size = max(
        r["output_bytes"] for r in records if r.get("engine") == "pardox" and "output_bytes" in r
    )
    lines += [
        "",
        "Guardas: filas esperadas sales=86,490, ecommerce=9,947, "
        "exchange_rates=730; no se publican etapas sub-ms con filas.",
        "El dataset de 86k filas es pequeño y no generaliza. Escala opcional: sales x10/x100 en "
        "un directorio temporal usando CAFENORTE_DATA_DIR, sin tocar datos/.",
        "Salida serializada: PardoX escribe .prdx y Polars escribe CSV equivalente; el tamaño "
        "exacto queda en cada línea JSONL de logs/.",
        f"Tamaño medido: CSV Polars={polars_size} bytes; PRDX PardoX={pardox_size} bytes.",
    ]
    (logs / "benchmark_latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / "artifacts/evidence/benchmark.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("benchmark completed")


if __name__ == "__main__":
    main()
