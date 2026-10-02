# PardoX 0.3.4 PRDX reproduction

This case uses the repository's `datos/sales.csv` only as a source to create temporary
scaled copies; no source data is written to this directory. It targets macOS arm64 and
PardoX 0.3.4.

```bash
set -a; source .env; set +a
uv run python artifacts/evidence/pardox-0.3.4-prdx-repro/reproduce.py --multiplier 5 --repeat 5
```

The script performs `read_csv -> to_prdx -> load_prdx` and compares the recovered
`venta_id` sequence with the source. With the installed 0.3.4 wheel, x2 is clean while
x5 and x10 are not. The PostgreSQL `write_sql_prdx` path shows the same failure.

The local core inspection points to variable-width UTF-8 offset state being concatenated
across blocks without a cumulative byte offset in `prdx_writer.rs`; this is reported as a
PardoX bug. The installed package is not modified.
