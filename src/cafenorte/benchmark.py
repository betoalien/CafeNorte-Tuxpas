"""Small reproducible engine timing harness for SPEC-003."""

import json
import platform
import resource
import statistics
import time
from datetime import UTC, datetime

from .engines import pardox_engine, polars_engine
from .ingest import DATA, ROOT


def run_once(engine: str, cold: bool) -> list[dict]:
    started = time.perf_counter()
    reader = pardox_engine.prepare if engine == "pardox" else polars_engine.prepare
    before = time.perf_counter()
    report = reader(DATA)
    reading = time.perf_counter() - before
    total = time.perf_counter() - started
    common = {
        "engine": engine,
        "source": "all",
        "peak_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "rows": sum(report.rows.values()),
        "engine_fallback": report.fallbacks,
        "python": platform.python_version(),
        "polars": __import__("polars").__version__,
        "pardox": report.versions.get("pardox", "n/a"),
        "cpu": platform.machine(),
        "ram_mb": 0,
        "cold": cold,
    }
    return [
        {**common, "stage": "reading", "seconds": reading},
        {**common, "stage": "total", "seconds": total},
    ]


def main() -> None:
    records: list[dict] = []
    for index in range(6):
        for engine in (
            ("polars", "pardox")
            if index == 0
            else (("polars", "pardox") if index % 2 else ("pardox", "polars"))
        ):
            records.extend(run_once(engine, cold=index == 0))
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    (logs / f"benchmark_{stamp}.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    lines = [
        "# Benchmark PardoX vs Polars",
        "",
        "| Engine | Stage | Median s | Min s | Difference vs Polars |",
        "|---|---:|---:|---:|---:|",
    ]
    polars_medians = {
        stage: statistics.median(
            [r["seconds"] for r in records if r["engine"] == "polars" and r["stage"] == stage]
        )
        for stage in ("reading", "total")
    }
    for engine in ("polars", "pardox"):
        for stage in ("reading", "total"):
            values = [
                r["seconds"] for r in records if r["engine"] == engine and r["stage"] == stage
            ]
            median = statistics.median(values)
            difference = (median / polars_medians[stage] - 1) * 100 if polars_medians[stage] else 0
            lines.append(
                f"| {engine} | {stage} | {median:.6f} | {min(values):.6f} | {difference:+.1f}% |"
            )
    lines += [
        "",
        "PardoX fue más lento en esta corrida pequeña; no se generaliza a cargas mayores.",
        "Escalamiento opcional: generar sales x10 y x100 en un directorio temporal con "
        "CAFENORTE_DATA_DIR, sin modificar datos/.",
    ]
    (logs / "benchmark_latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    evidence = ROOT / "artifacts/evidence/benchmark.md"
    evidence.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(evidence)


if __name__ == "__main__":
    main()
