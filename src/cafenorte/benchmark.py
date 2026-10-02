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

from .engines.pardox_engine import connection_url
from .ingest import DATA, ROOT, connect


def worker(engine: str, result_path: Path) -> None:
    import polars as pl

    started = time.perf_counter()
    if engine == "pardox":
        import pardox as px

        frame = px.read_csv(str(DATA / "sales.csv"))
        version = px.__version__
        read_seconds = time.perf_counter() - started
    elif engine == "polars":
        frame = pl.read_csv(DATA / "sales.csv")
        version = "n/a"
        read_seconds = time.perf_counter() - started
    else:
        import csv

        with (DATA / "sales.csv").open(newline="", encoding="utf-8") as source:
            frame = list(csv.DictReader(source))
        version = "n/a"
        read_seconds = time.perf_counter() - started
    before = time.perf_counter()
    if engine == "pardox":
        frame.cast("cantidad", "Int64")
        frame.cast("monto", "Float64")
        frame.validate_contract({"columns": {"cantidad": {"min": 1}, "monto": {"min": 0}}})
    elif engine == "polars":
        frame = frame.with_columns(
            pl.col("cantidad").cast(pl.Int64), pl.col("monto").cast(pl.Float64)
        ).filter((pl.col("cantidad") >= 1) & (pl.col("monto") > 0) & (pl.col("moneda") == "MXN"))
    else:
        for row in frame:
            row["cantidad"] = int(row["cantidad"])
            row["monto"] = float(row["monto"])
        frame = [
            row
            for row in frame
            if row["cantidad"] >= 1 and row["monto"] > 0 and row["moneda"] == "MXN"
        ]
    validate_seconds = time.perf_counter() - before
    before = time.perf_counter()
    if engine == "pardox":
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
    transform_seconds = time.perf_counter() - before
    aggregate_seconds = time.perf_counter() - before
    conn_url = connection_url()
    table = "silver_pardox.benchmark_sales"
    load_start = time.perf_counter()
    import psycopg

    with psycopg.connect(conn_url) as conn, conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS silver_pardox.benchmark_sales")
        cur.execute(
            "CREATE TABLE silver_pardox.benchmark_sales (venta_id text, fecha_hora text, "
            "tienda_id text, sku text, cantidad bigint, monto double precision, "
            "moneda text, tipo_comprobante text)"
        )
    if engine == "pardox":
        import pardox as px

        loaded = frame.to_sql(conn_url, table, mode="append")
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
    if engine == "pardox":
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
    if engine == "pardox":
        import pardox as px

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
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT count(*), coalesce(sum(cantidad), 0), coalesce(sum(monto), 0) "
            "FROM silver_pardox.benchmark_sales"
        )
        loaded_check = cur.fetchone()
        cur.execute(
            "SELECT tienda_id, count(*), sum(cantidad), sum(monto) "
            "FROM silver_pardox.benchmark_sales GROUP BY tienda_id ORDER BY tienda_id"
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
        stages["load_prdx"] = prdx_load_seconds
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
        engines = (
            ("polars", "pardox", "python") if index % 2 == 0 else ("pardox", "polars", "python")
        )
        for engine in engines:
            records.extend(run_subprocess(engine, cold=index == 0))
    expected = {"sales": 86490}
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
            "load_prdx",
            "total",
            "to_prdx",
        } and (record["rows_processed"] <= 0 or record["seconds"] < 0.001):
            raise RuntimeError(f"Benchmark sanity guard failed: {record}")
        if record.get("stage") == "load" and record.get("loaded") != 86490:
            raise RuntimeError(f"Benchmark load guard failed: {record}")
        if record.get("stage") == "load_prdx" and record.get("prdx_loaded") != 86490:
            raise RuntimeError(f"Benchmark PRDX load guard failed: {record}")
    signatures = {
        engine: next(
            r["aggregate_signature"]
            for r in records
            if r.get("engine") == engine and r.get("stage") == "aggregate"
        )
        for engine in ("polars", "pardox", "python")
    }
    if signatures["polars"] != signatures["pardox"] or signatures["polars"] != signatures["python"]:
        raise RuntimeError(f"Aggregate parity guard failed: {signatures}")
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
    for stage in (
        "read",
        "validate",
        "transform",
        "aggregate",
        "load",
        "write",
        "load_prdx",
        "total",
    ):
        medians = {}
        for engine in ("polars", "pardox", "python"):
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
            calls = {
                "polars": "pl.read_csv / DataFrame.write_database(engine=adbc)",
                "pardox": "px.read_csv / df.to_sql / px.write_sql_prdx",
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
