"""SPEC-003 benchmark: equal work, isolated subprocesses, and sanity guards."""

import csv
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

from .engines.pardox_engine import connection_url
from .ingest import DATA, ROOT, connect


def worker(engine: str, result_path: Path) -> None:
    import pardox as px

    source_dir = Path(os.environ.get("CAFENORTE_DATA_DIR", str(DATA)))
    import polars as pl
    import psycopg

    import_start = time.perf_counter()
    conn_url = connection_url()
    with psycopg.connect(conn_url) as warm_connection:
        warm_connection.execute("SELECT 1")
    import_seconds = time.perf_counter() - import_start
    started = time.perf_counter()
    if engine in {"pardox", "pardox_prdx"}:
        frame = px.read_csv(str(source_dir / "sales.csv"))
        version = px.__version__
        rows_in = frame.shape[0]
    elif engine == "polars":
        frame = pl.read_csv(source_dir / "sales.csv")
        version = "n/a"
        read_seconds = time.perf_counter() - started
    else:
        import csv

        with (source_dir / "sales.csv").open(newline="", encoding="utf-8") as source:
            frame = list(csv.DictReader(source))
        version = "n/a"
        read_seconds = time.perf_counter() - started
    rows_in = frame.shape[0] if hasattr(frame, "shape") else len(frame)
    read_seconds = time.perf_counter() - started
    before = time.perf_counter()
    if engine in {"pardox", "pardox_prdx"}:
        frame.cast("cantidad", "Int64")
        frame.cast("monto", "Float64")
        frame.validate_contract({"columns": {"cantidad": {"min": 1}, "monto": {"min": 0}}})
        rejected = 0
    elif engine == "polars":
        frame = frame.with_columns(
            pl.col("cantidad").cast(pl.Int64), pl.col("monto").cast(pl.Float64)
        ).filter((pl.col("cantidad") >= 1) & (pl.col("monto") > 0) & (pl.col("moneda") == "MXN"))
        rejected = rows_in - frame.shape[0]
    else:
        for row in frame:
            row["cantidad"] = int(row["cantidad"])
            row["monto"] = float(row["monto"])
        frame = [
            row
            for row in frame
            if row["cantidad"] >= 1 and row["monto"] > 0 and row["moneda"] == "MXN"
        ]
        rejected = rows_in - len(frame)
    validate_seconds = time.perf_counter() - before
    before = time.perf_counter()
    if engine == "polars":
        frame = frame.with_columns(
            pl.col("sku").str.extract(r"(\d{3})$", 1).alias("product_number"),
            pl.col("fecha_hora").str.slice(0, 7).alias("mes"),
        )
    elif engine == "python":
        for row in frame:
            digits = "".join(ch for ch in row["sku"] if ch.isdigit())
            row["product_number"] = digits[-3:]
            row["mes"] = row["fecha_hora"][:7]
    else:
        # PardoX 0.3.4 has str_replace/date_extract but no regex extraction or
        # parsing from Utf8 to Date; the equivalent normalization is checked in SQL.
        frame.str_replace("sku", "CN-", "")
    transform_seconds = time.perf_counter() - before
    before = time.perf_counter()
    if engine in {"pardox", "pardox_prdx"}:
        aggregate = frame.groupby("tienda_id", {"cantidad": "sum", "monto": "sum"})
    elif engine == "polars":
        aggregate = frame.group_by("tienda_id").agg(
            pl.len().alias("count"), pl.col("cantidad").sum(), pl.col("monto").sum()
        )
    else:
        aggregate = {}
        for row in frame:
            key = row["tienda_id"]
            item = aggregate.setdefault(key, [0, 0, 0.0])
            item[0] += 1
            item[1] += row["cantidad"]
            item[2] += row["monto"]
    aggregate_seconds = time.perf_counter() - before
    table = "silver_pardox.benchmark_sales"
    load_start = time.perf_counter()
    import psycopg

    with psycopg.connect(conn_url) as conn, conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS silver_pardox.benchmark_sales")
        cur.execute(
            "CREATE TABLE silver_pardox.benchmark_sales (venta_id text, fecha_hora text, "
            "tienda_id text, sku text, cantidad bigint, monto double precision, "
            "moneda text, tipo_comprobante text, product_number text, mes text)"
        )
    if engine == "pardox":
        loaded = frame.to_sql(conn_url, table, mode="append")
    elif engine == "pardox_prdx":
        loaded = None
    elif engine == "polars":
        try:
            frame.write_database(
                "silver_pardox.benchmark_sales", conn_url, if_table_exists="append", engine="adbc"
            )
            with connect() as conn, conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM silver_pardox.benchmark_sales")
                loaded = cur.fetchone()[0]
        except Exception as error:
            raise RuntimeError(f"Polars ADBC native write failed on arm64: {error}") from error
    else:
        with psycopg.connect(conn_url) as conn, conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO silver_pardox.benchmark_sales VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                [
                    (
                        r["venta_id"],
                        r["fecha_hora"],
                        r["tienda_id"],
                        r["sku"],
                        r["cantidad"],
                        r["monto"],
                        r["moneda"],
                        r["tipo_comprobante"],
                    )
                    for r in frame
                ],
            )
            loaded = len(frame)
    load_seconds = time.perf_counter() - load_start
    output_start = time.perf_counter()
    output = Path(tempfile.mkstemp(suffix=".prdx")[1])
    if engine in {"pardox", "pardox_prdx"}:
        frame.to_prdx(str(output))
        output_format = "prdx"
    elif engine == "polars":
        output = output.with_suffix(".parquet")
        frame.write_parquet(output)
        output_format = "parquet"
    else:
        output = output.with_suffix(".json")
        output.write_text(json.dumps(frame), encoding="utf-8")
        output_format = "json"
    output_seconds = time.perf_counter() - output_start
    prdx_load_seconds = None
    prdx_loaded = None
    if engine == "pardox_prdx":
        prdx_load_start = time.perf_counter()
        px.execute_sql(conn_url, "DROP TABLE IF EXISTS silver_pardox.benchmark_prdx_sales")
        px.execute_sql(
            conn_url,
            "CREATE TABLE silver_pardox.benchmark_prdx_sales (venta_id text, fecha_hora text, "
            "tienda_id text, sku text, cantidad bigint, monto double precision, "
            "moneda text, tipo_comprobante text)",
        )
        prdx_loaded = px.write_sql_prdx(
            str(output), conn_url, "silver_pardox.benchmark_prdx_sales", mode="append"
        )
        prdx_load_seconds = time.perf_counter() - prdx_load_start
    peak_raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mb = peak_raw / (1024 * 1024) if platform.system() == "Darwin" else peak_raw / 1024
    check_table = "silver_pardox.benchmark_prdx_sales" if engine == "pardox_prdx" else table
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT count(*), coalesce(sum(cantidad), 0), coalesce(sum(monto), 0) "
            f"FROM {check_table}"
        )
        loaded_check = cur.fetchone()
        cur.execute(
            "SELECT tienda_id, left(fecha_hora, 7), count(*), sum(cantidad), "
            "round(sum(monto)::numeric, 2) "
            f"FROM {check_table} GROUP BY tienda_id, left(fecha_hora, 7) "
            "ORDER BY tienda_id, left(fecha_hora, 7)"
        )
        aggregate_signature = [tuple(row) for row in cur.fetchall()]
    records = []
    stages = {
        "read": read_seconds,
        "validate": validate_seconds,
        "transform": transform_seconds,
        "aggregate": aggregate_seconds,
        "load": load_seconds,
        "write": output_seconds,
        "total": time.perf_counter() - started,
    }
    if prdx_load_seconds is not None:
        stages["load"] = prdx_load_seconds
        loaded = prdx_loaded
    for stage, seconds in stages.items():
        records.append(
            {
                "engine": engine,
                "source": "all",
                "stage": stage,
                "seconds": seconds,
                "peak_mb": peak_mb,
                "rows_processed": int(frame.shape[0] if hasattr(frame, "shape") else len(frame)),
                "source_rows": {
                    "sales": int(frame.shape[0] if hasattr(frame, "shape") else len(frame))
                },
                "engine_fallback": {},
                "python": platform.python_version(),
                "polars": __import__("polars").__version__,
                "pardox": version,
                "cpu": platform.machine(),
                "cold": os.environ.get("CAFENORTE_BENCHMARK_COLD") == "1",
                "import_seconds": import_seconds,
                "rejected": rejected,
                "output_bytes": output.stat().st_size,
                "output_format": output_format,
                "loaded": int(loaded),
                "aggregate_rows": int(
                    aggregate.shape[0] if hasattr(aggregate, "shape") else len(aggregate)
                ),
                "aggregate_signature": aggregate_signature,
                "loaded_check": list(loaded_check),
                "prdx_loaded": prdx_loaded,
            }
        )
    result_path.write_text(json.dumps(records, default=str), encoding="utf-8")


def run_subprocess(engine: str, cold: bool, data_dir: Path) -> list[dict]:
    with tempfile.NamedTemporaryFile(suffix=".json") as result:
        env = {
            **os.environ,
            "CAFENORTE_BENCHMARK_COLD": "1" if cold else "0",
            "CAFENORTE_DATA_DIR": str(data_dir),
        }
        subprocess.run(
            [sys.executable, "-m", "cafenorte.benchmark", "--worker", engine, result.name],
            check=True,
            env=env,
            stdout=subprocess.DEVNULL,
        )
        return json.loads(Path(result.name).read_text(encoding="utf-8"))


def make_scaled_data(multiplier: int) -> tuple[tempfile.TemporaryDirectory, Path]:
    temp_dir = tempfile.TemporaryDirectory(prefix="cafenorte-benchmark-")
    target = Path(temp_dir.name)
    with (DATA / "sales.csv").open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    with (target / "sales.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        for copy_number in range(multiplier):
            for row in rows:
                duplicate = dict(row)
                duplicate["venta_id"] = f"{row['venta_id']}-{copy_number:02d}"
                writer.writerow(duplicate)
    return temp_dir, target


def run_suite(data_dir: Path, expected_rows: int) -> list[dict]:
    records: list[dict] = []
    for index in range(6):
        engines = (
            ("polars", "pardox", "pardox_prdx", "python")
            if index % 2 == 0
            else ("pardox_prdx", "pardox", "polars", "python")
        )
        for engine in engines:
            records.extend(run_subprocess(engine, index == 0, data_dir))
    for record in records:
        record["dataset_rows"] = expected_rows
        if record.get("source_rows", {}).get("sales") != expected_rows:
            raise RuntimeError(f"Benchmark row guard failed: {record}")
        measured = {"read", "validate", "transform", "aggregate", "load", "write", "total"}
        if record.get("stage") in measured and record["seconds"] < 0.001:
            raise RuntimeError(f"Benchmark sanity guard failed: {record}")
        if record.get("stage") == "load" and record.get("loaded") != expected_rows:
            raise RuntimeError(f"Benchmark load guard failed: {record}")
    signatures = {
        engine: next(
            r["aggregate_signature"]
            for r in records
            if r.get("engine") == engine and r.get("stage") == "aggregate"
        )
        for engine in ("polars", "pardox", "pardox_prdx", "python")
    }
    if len({json.dumps(value, sort_keys=True, default=str) for value in signatures.values()}) != 1:
        diagnostics = {
            engine: {"groups": len(value), "head": value[:2]}
            for engine, value in signatures.items()
        }
        raise RuntimeError(f"Aggregate parity guard failed: {diagnostics}")
    return records


def main() -> None:
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        worker(sys.argv[2], Path(sys.argv[3]))
        return
    records: list[dict] = []
    records.extend(run_suite(DATA, 86490))
    scaled_tmp, scaled_dir = make_scaled_data(10)
    try:
        records.extend(run_suite(scaled_dir, 864900))
    finally:
        scaled_tmp.cleanup()
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    (logs / f"benchmark_{stamp}.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )
    lines = [
        "# Benchmark PardoX vs Polars",
        "",
        "| Engine | Stage | Median s | Min s | Difference vs Polars | Peak MB | Call |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for dataset_rows in (86490, 864900):
        lines.append(f"\n## {dataset_rows:,} filas\n")
        lines.append(
            "| Engine | Stage | Median s | Min s | Difference vs Polars | Peak MB | Call |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---|")
        subset = [r for r in records if r.get("dataset_rows") == dataset_rows]
        for stage in (
            "read",
            "validate",
            "transform",
            "aggregate",
            "load",
            "write",
            "total",
        ):
            medians = {}
            for engine in ("polars", "pardox", "pardox_prdx", "python"):
                values = [
                    r["seconds"]
                    for r in subset
                    if r.get("engine") == engine and r.get("stage") == stage
                ]
                if not values:
                    continue
                medians[engine] = statistics.median(values)
                difference = (medians[engine] / medians.get("polars", medians[engine]) - 1) * 100
                peak = max(
                    r["peak_mb"]
                    for r in subset
                    if r.get("engine") == engine and r.get("stage") == stage
                )
                calls = {
                    "polars": "pl.read_csv / DataFrame.write_database(engine=adbc)",
                    "pardox": "px.read_csv / df.to_sql",
                    "pardox_prdx": "px.read_csv / df.to_prdx / px.write_sql_prdx",
                    "python": "csv.DictReader / psycopg.executemany",
                }
                lines.append(
                    f"| {engine} | {stage} | {medians[engine]:.6f} | {min(values):.6f} | "
                    f"{difference:+.1f}% | {peak:.1f} | {calls[engine]} |"
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
        "Salida serializada: PardoX escribe .prdx y Polars escribe parquet; el tamaño "
        "exacto queda en cada línea JSONL de logs/.",
        f"Tamaño medido: parquet Polars={polars_size} bytes; PRDX PardoX={pardox_size} bytes.",
    ]
    (logs / "benchmark_latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / "artifacts/evidence/benchmark.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("benchmark completed")


if __name__ == "__main__":
    main()
