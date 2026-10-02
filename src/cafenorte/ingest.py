"""Read-only Bronze ingestion and transactional Polars/Pydantic Silver load."""

import csv
import hashlib
import json
import os
import re
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID, uuid4

import polars as pl
import psycopg
from pydantic import ValidationError

from .contracts import (
    CONTRACT_VERSION,
    EcommerceOrderRecord,
    ExchangeRateRecord,
    Manifest,
    MappingRecord,
    ProductRecord,
    QuarantineRecord,
    SalesRecord,
    SnapshotRecord,
    StoreRecord,
)
from .engines import pardox_engine, polars_engine
from .engines.common import validate_engine
from .engines.pos_sales import build_pos_sales_pardox

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("CAFENORTE_DATA_DIR", str(ROOT / "datos")))
MANIFEST_DIR = ROOT / "artifacts" / "manifests"
T = TypeVar("T")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now() -> datetime:
    return datetime.now(UTC)


def product_number(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(\d{3})(?:-[A-Za-z])?$", value)
    return match.group(1) if match else None


def normalized_handle(value: str) -> str:
    import unicodedata

    base = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", base.lower())


def parse_records[T](
    source: str,
    rows: list[dict[str, Any]],
    model: type[T],
    key: Callable[[dict[str, Any]], str],
    run_id: UUID,
    allowed_payload: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> tuple[list[T], list[QuarantineRecord]]:
    accepted: list[T] = []
    rejected: list[QuarantineRecord] = []
    for row in rows:
        try:
            accepted.append(model.model_validate(row))
        except ValidationError as exc:
            payload = allowed_payload(row) if allowed_payload else row
            rejected.append(
                QuarantineRecord(
                    source=source,
                    record_key=key(row),
                    reason=str(exc.errors()[0]["msg"]),
                    payload=payload,
                    run_id=run_id,
                )
            )
    return accepted, rejected


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def source_manifest(
    path: Path,
    run_id: UUID,
    started: datetime,
    input_count: int,
    accepted: int,
    rejected: int,
    sha_before: str,
    sha_after: str,
    load_mode: str = "full",
) -> Manifest:
    return Manifest(
        run_id=run_id,
        source_file=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name,
        sha256_before=sha_before,
        sha256_after=sha_after,
        size_bytes=path.stat().st_size,
        input_count=input_count,
        accepted_count=accepted,
        rejected_count=rejected,
        contract_version=CONTRACT_VERSION,
        started_at=started,
        completed_at=now(),
        load_mode=load_mode,
    )


def connect() -> psycopg.Connection:
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ.get("PIPELINE_USER", "pipeline"),
        password=os.environ["PIPELINE_PASSWORD"],
    )


DDL = """
CREATE TABLE IF NOT EXISTS audit.run_log (
  run_id uuid PRIMARY KEY, started_at timestamptz NOT NULL, completed_at timestamptz,
  status text NOT NULL, input_count bigint NOT NULL DEFAULT 0,
  accepted_count bigint NOT NULL DEFAULT 0, rejected_count bigint NOT NULL DEFAULT 0,
  error_message text, load_mode text NOT NULL DEFAULT 'full'
);
CREATE TABLE IF NOT EXISTS audit.ingestion_manifest (
  run_id uuid NOT NULL, source_file text NOT NULL, sha256_before text NOT NULL,
  sha256_after text NOT NULL, size_bytes bigint NOT NULL, input_count bigint NOT NULL,
  accepted_count bigint NOT NULL, rejected_count bigint NOT NULL, contract_version text NOT NULL,
  started_at timestamptz NOT NULL, completed_at timestamptz NOT NULL,
  load_mode text NOT NULL DEFAULT 'full',
  PRIMARY KEY (run_id, source_file)
);
ALTER TABLE audit.run_log ADD COLUMN IF NOT EXISTS load_mode text NOT NULL DEFAULT 'full';
ALTER TABLE audit.ingestion_manifest ADD COLUMN IF NOT EXISTS load_mode text NOT NULL DEFAULT 'full';
CREATE TABLE IF NOT EXISTS audit.quarantine (
  quarantine_id bigserial PRIMARY KEY, source text NOT NULL, record_key text NOT NULL,
  reason text NOT NULL, payload jsonb NOT NULL, run_id uuid NOT NULL,
  quarantined_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS silver.pos_sales (
  venta_id text PRIMARY KEY, fecha_hora_original text NOT NULL,
  fecha_hora_normalizada timestamp NOT NULL,
  tienda_id text NOT NULL, sku text NOT NULL, product_number text, cantidad bigint NOT NULL,
  monto numeric(18,2) NOT NULL, moneda text NOT NULL, tipo_comprobante text NOT NULL,
  run_id uuid NOT NULL, ingested_at timestamptz NOT NULL, row_hash text NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS silver.stores (
  tienda_id text PRIMARY KEY, ciudad text NOT NULL, region text NOT NULL, timezone text NOT NULL,
  run_id uuid NOT NULL, ingested_at timestamptz NOT NULL, row_hash text NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS silver.products (
  sku_erp text PRIMARY KEY, product_number text, nombre text NOT NULL, categoria text NOT NULL,
  cost_history jsonb NOT NULL, run_id uuid NOT NULL, ingested_at timestamptz NOT NULL, row_hash text NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS silver.sku_mappings (
  sku_pos text PRIMARY KEY, sku_erp text, handle text, run_id uuid NOT NULL,
  ingested_at timestamptz NOT NULL, row_hash text NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS silver.inventory_snapshots (
  fecha date NOT NULL, tienda_id text NOT NULL, sku_erp text NOT NULL, stock_quantity integer,
  stock_raw_value text NOT NULL, quality_status text NOT NULL, quality_reason text NOT NULL,
  run_id uuid NOT NULL, ingested_at timestamptz NOT NULL, row_hash text NOT NULL DEFAULT '', PRIMARY KEY (fecha, tienda_id, sku_erp)
);
CREATE TABLE IF NOT EXISTS silver.ecommerce_orders (
  order_id text PRIMARY KEY, fecha timestamp NOT NULL, product_handle text NOT NULL,
  product_number text,
  handle_name_normalized text NOT NULL, cantidad bigint NOT NULL, amount numeric(18,2) NOT NULL,
  currency text NOT NULL, run_id uuid NOT NULL, ingested_at timestamptz NOT NULL, row_hash text NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS silver.exchange_rates (
  fecha date NOT NULL, currency text NOT NULL, rate_to_mxn numeric(18,6) NOT NULL,
  fx_quality_flag text NOT NULL, run_id uuid NOT NULL, ingested_at timestamptz NOT NULL, row_hash text NOT NULL DEFAULT '',
  PRIMARY KEY (fecha, currency)
);
ALTER TABLE silver.pos_sales ADD COLUMN IF NOT EXISTS row_hash text NOT NULL DEFAULT '';
ALTER TABLE silver.stores ADD COLUMN IF NOT EXISTS row_hash text NOT NULL DEFAULT '';
ALTER TABLE silver.products ADD COLUMN IF NOT EXISTS row_hash text NOT NULL DEFAULT '';
ALTER TABLE silver.sku_mappings ADD COLUMN IF NOT EXISTS row_hash text NOT NULL DEFAULT '';
ALTER TABLE silver.inventory_snapshots ADD COLUMN IF NOT EXISTS row_hash text NOT NULL DEFAULT '';
ALTER TABLE silver.ecommerce_orders ADD COLUMN IF NOT EXISTS row_hash text NOT NULL DEFAULT '';
ALTER TABLE silver.exchange_rates ADD COLUMN IF NOT EXISTS row_hash text NOT NULL DEFAULT '';
"""


def insert_rows(cur: psycopg.Cursor, sql: str, rows: list[tuple[Any, ...]]) -> None:
    if rows:
        cur.executemany(sql, rows)


def add_row_hashes(data: dict[str, list[tuple[Any, ...]]]) -> None:
    for name, rows in data.items():
        data[name] = [
            row
            if isinstance(row[-1], str) and len(row[-1]) == 64
            else row[:-2] + row[-2:] + (row_hash(row[:-2]),)
            for row in rows
        ]


def row_hash(values: tuple[Any, ...]) -> str:
    return hashlib.sha256(json.dumps(values, default=str, sort_keys=True).encode()).hexdigest()


def business_key(name: str, row: tuple[Any, ...]) -> Any:
    return {
        "sales": row[0],
        "stores": row[0],
        "products": row[0],
        "mappings": row[0],
        "snapshots": row[:3],
        "orders": row[0],
        "rates": row[:2],
    }[name]


TABLES = {
    "sales": ("silver.pos_sales", "venta_id"),
    "stores": ("silver.stores", "tienda_id"),
    "products": ("silver.products", "sku_erp"),
    "mappings": ("silver.sku_mappings", "sku_pos"),
    "snapshots": ("silver.inventory_snapshots", "(fecha, tienda_id, sku_erp)"),
    "orders": ("silver.ecommerce_orders", "order_id"),
    "rates": ("silver.exchange_rates", "(fecha, currency)"),
}


def ensure_tables() -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)


def load(
    run_id: UUID,
    manifests: list[Manifest],
    quarantines: list[QuarantineRecord],
    data: dict[str, Any],
    source_paths: list[Path],
    hashes_before: dict[Path, str],
    table_modes: dict[str, str],
    target_schema: str = "silver",
) -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            DDL if target_schema == "silver" else DDL.replace("silver.", f"{target_schema}.")
        )
        add_row_hashes(data)
        tables = {
            name: (f"{target_schema}.{table.split('.', 1)[1]}", keys)
            for name, (table, keys) in TABLES.items()
        }
        for name, (table, key_columns) in tables.items():
            mode = table_modes[name]
            if mode == "full":
                cur.execute(f"DELETE FROM {table}")
            elif mode == "incremental":
                key_sql = key_columns.strip("()")
                cur.execute(f"SELECT {key_sql}, row_hash FROM {table}")
                existing = {
                    (row[:-1] if len(row) > 2 else row[0]): row[-1] for row in cur.fetchall()
                }
                data[name] = [row for row in data[name] if business_key(name, row) not in existing]
            elif mode == "skipped":
                data[name] = []
        insert_rows(
            cur,
            f"INSERT INTO {tables['sales'][0]} VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            data["sales"],
        )
        insert_rows(
            cur, f"INSERT INTO {tables['stores'][0]} VALUES (%s,%s,%s,%s,%s,%s,%s)", data["stores"]
        )
        insert_rows(
            cur,
            f"INSERT INTO {tables['products'][0]} VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            data["products"],
        )
        insert_rows(
            cur, f"INSERT INTO {tables['mappings'][0]} VALUES (%s,%s,%s,%s,%s,%s)", data["mappings"]
        )
        insert_rows(
            cur,
            f"INSERT INTO {tables['snapshots'][0]} VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            data["snapshots"],
        )
        insert_rows(
            cur,
            f"INSERT INTO {tables['orders'][0]} VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            data["orders"],
        )
        insert_rows(
            cur, f"INSERT INTO {tables['rates'][0]} VALUES (%s,%s,%s,%s,%s,%s,%s)", data["rates"]
        )
        hashes_after = {path: sha256(path) for path in source_paths}
        changed = [path for path in source_paths if hashes_before[path] != hashes_after[path]]
        if changed:
            message = "Source changed during ingestion: " + ", ".join(str(path) for path in changed)
            raise RuntimeError(message)
        for manifest, path in zip(manifests, source_paths, strict=True):
            manifest.sha256_after = hashes_after[path]
        insert_rows(
            cur,
            "INSERT INTO audit.quarantine "
            "(source,record_key,reason,payload,run_id) VALUES (%s,%s,%s,%s,%s)",
            [
                (
                    q.source,
                    q.record_key,
                    q.reason,
                    json.dumps(q.payload, ensure_ascii=False),
                    q.run_id,
                )
                for q in quarantines
            ],
        )
        insert_rows(
            cur,
            "INSERT INTO audit.ingestion_manifest VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            [tuple(m.model_dump().values()) for m in manifests],
        )
        total_input = sum(m.input_count for m in manifests)
        total_accepted = sum(m.accepted_count for m in manifests)
        total_rejected = sum(m.rejected_count for m in manifests)
        cur.execute(
            "INSERT INTO audit.run_log VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                run_id,
                manifests[0].started_at,
                now(),
                "succeeded",
                total_input,
                total_accepted,
                total_rejected,
                None,
                json.dumps({m.source_file: m.load_mode for m in manifests}, sort_keys=True),
            ),
        )


def update_run_status(run_id: UUID, status: str, error_message: str | None = None) -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE audit.run_log SET status = %s, completed_at = %s, error_message = %s "
            "WHERE run_id = %s",
            (status, now(), error_message, run_id),
        )


def record_failed(run_id: UUID, started: datetime, error: Exception) -> None:
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO audit.run_log "
                "(run_id, started_at, completed_at, status, error_message) "
                "VALUES (%s, %s, %s, 'failed', %s) "
                "ON CONFLICT (run_id) DO UPDATE SET status = 'failed', "
                "completed_at = EXCLUDED.completed_at, error_message = EXCLUDED.error_message",
                (run_id, started, now(), str(error)),
            )
    except psycopg.Error:
        # A failed connection before init cannot create an audit row.
        pass


def record_skipped(run_id: UUID, started: datetime) -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO audit.run_log "
            "(run_id, started_at, completed_at, status, load_mode) "
            "VALUES (%s, %s, %s, 'skipped', 'skipped')",
            (run_id, started, now()),
        )


def snapshot_to_silver(
    record: SnapshotRecord, run_id: UUID, ingested_at: datetime
) -> tuple[Any, ...]:
    is_unknown = record.cantidad_en_stock == "N/A"
    return (
        record.fecha,
        record.tienda_id,
        record.sku_erp,
        None if is_unknown else record.cantidad_en_stock,
        str(record.cantidad_en_stock),
        "unknown" if is_unknown else "valid",
        "N/A means unknown" if is_unknown else "",
        run_id,
        ingested_at,
    )


def _run(run_id: UUID, started: datetime, force: bool = False, engine: str = "polars") -> str:
    validate_engine(engine)
    engine_metadata = (
        pardox_engine.prepare(DATA) if engine == "pardox" else polars_engine.prepare(DATA)
    )
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        DATA / "sales.csv",
        DATA / "inventory.json",
        DATA / "ecommerce_orders.parquet",
        DATA / "exchange_rates.csv",
    ]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    hashes_before = {path: sha256(path) for path in paths}
    ensure_tables()
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT source_file, sha256_after FROM audit.ingestion_manifest "
            "WHERE run_id = (SELECT run_id FROM audit.run_log WHERE status = 'succeeded' "
            "AND load_mode <> 'skipped' ORDER BY started_at DESC LIMIT 1)"
        )
        previous = {row[0]: row[1] for row in cur.fetchall()}
    source_names = {
        path: str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name
        for path in paths
    }
    if (
        not force
        and previous
        and all(
            previous.get(source_names[path]) == digest for path, digest in hashes_before.items()
        )
    ):
        record_skipped(run_id, started)
        result = {"run_id": str(run_id), "load_mode": "skipped"}
        print(json.dumps(result))
        return "skipped"
    sales_rows = read_csv(paths[0])
    for row in sales_rows:
        row["cantidad"] = int(row["cantidad"])
        row["monto"] = Decimal(row["monto"])
    sales, q_sales = parse_records(
        "sales.csv", sales_rows, SalesRecord, lambda r: r.get("venta_id", ""), run_id
    )
    inventory = json.loads(paths[1].read_text(encoding="utf-8"))
    stores, q_stores = parse_records(
        "inventory.json:tiendas_info",
        inventory["tiendas_info"],
        StoreRecord,
        lambda r: r.get("tienda_id", ""),
        run_id,
    )
    mappings, q_mappings = parse_records(
        "inventory.json:sku_mappings",
        inventory["sku_mappings"],
        MappingRecord,
        lambda r: r.get("sku_pos", ""),
        run_id,
    )
    products, q_products = parse_records(
        "inventory.json:catalogo",
        inventory["catalogo"]["productos"],
        ProductRecord,
        lambda r: r.get("sku_erp", ""),
        run_id,
    )
    snapshot_rows = inventory["snapshots"]
    snapshots, q_snapshots = parse_records(
        "inventory.json:snapshots",
        snapshot_rows,
        SnapshotRecord,
        lambda r: f"{r.get('fecha')}|{r.get('tienda_id')}|{r.get('sku_erp')}",
        run_id,
    )
    seen: set[tuple[Any, ...]] = set()
    unique_snapshots: list[SnapshotRecord] = []
    for record in snapshots:
        key = (record.fecha, record.tienda_id, record.sku_erp)
        if key in seen:
            q_snapshots.append(
                QuarantineRecord(
                    source="inventory.json:snapshots",
                    record_key="|".join(map(str, key)),
                    reason="duplicate_snapshot_key",
                    payload=record.model_dump(mode="json"),
                    run_id=run_id,
                )
            )
        else:
            seen.add(key)
            unique_snapshots.append(record)
    orders_df = pl.read_parquet(
        paths[2], columns=["order_id", "fecha", "product_handle", "cantidad", "amount", "currency"]
    )
    orders_rows = orders_df.to_dicts()
    for row in orders_rows:
        row["fecha"] = datetime.fromisoformat(row["fecha"])
        row["amount"] = Decimal(str(row["amount"]))
    orders, q_orders = parse_records(
        "ecommerce_orders.parquet",
        orders_rows,
        EcommerceOrderRecord,
        lambda r: r.get("order_id", ""),
        run_id,
    )
    rate_rows = read_csv(paths[3])
    for row in rate_rows:
        row["rate_to_mxn"] = Decimal(row["rate_to_mxn"])
    rates, q_rates = parse_records(
        "exchange_rates.csv",
        rate_rows,
        ExchangeRateRecord,
        lambda r: f"{r.get('fecha')}|{r.get('currency')}",
        run_id,
    )
    dates = {rate.fecha for rate in rates}
    rates.extend(
        ExchangeRateRecord(fecha=day, currency="MXN", rate_to_mxn=Decimal("1.0"))
        for day in sorted(dates)
    )
    manifests = [
        source_manifest(
            paths[0],
            run_id,
            started,
            len(sales_rows),
            len(sales),
            len(q_sales),
            hashes_before[paths[0]],
            hashes_before[paths[0]],
        ),
        source_manifest(
            paths[1],
            run_id,
            started,
            len(inventory["tiendas_info"])
            + len(inventory["sku_mappings"])
            + len(inventory["catalogo"]["productos"])
            + len(snapshot_rows),
            len(stores) + len(mappings) + len(products) + len(unique_snapshots),
            len(q_stores) + len(q_mappings) + len(q_products) + len(q_snapshots),
            hashes_before[paths[1]],
            hashes_before[paths[1]],
        ),
        source_manifest(
            paths[2],
            run_id,
            started,
            len(orders_rows),
            len(orders),
            len(q_orders),
            hashes_before[paths[2]],
            hashes_before[paths[2]],
        ),
        source_manifest(
            paths[3],
            run_id,
            started,
            len(rate_rows),
            len(rate_rows) - len(q_rates),
            len(q_rates),
            hashes_before[paths[3]],
            hashes_before[paths[3]],
        ),
    ]
    ingested_at = now()
    original_sales_dates = {row["venta_id"]: row["fecha_hora"] for row in sales_rows}
    data = {
        "sales": [
            (
                x.venta_id,
                original_sales_dates[x.venta_id],
                x.fecha_hora,
                x.tienda_id,
                x.sku,
                product_number(x.sku),
                x.cantidad,
                x.monto,
                x.moneda,
                x.tipo_comprobante,
                run_id,
                ingested_at,
            )
            for x in sales
        ],
        "stores": [
            (x.tienda_id, x.ciudad, x.region, x.timezone, run_id, ingested_at) for x in stores
        ],
        "products": [
            (
                x.sku_erp,
                product_number(x.sku_erp),
                x.nombre,
                x.categoria,
                json.dumps([c.model_dump(mode="json") for c in x.cost_history]),
                run_id,
                ingested_at,
            )
            for x in products
        ],
        "mappings": [(x.sku_pos, x.sku_erp, x.handle, run_id, ingested_at) for x in mappings],
        "snapshots": [snapshot_to_silver(x, run_id, ingested_at) for x in unique_snapshots],
        "orders": [
            (
                x.order_id,
                x.fecha,
                x.product_handle,
                product_number(x.product_handle),
                normalized_handle(re.sub(r"[-_]?\d{3}$", "", x.product_handle)),
                x.cantidad,
                x.amount,
                x.currency,
                run_id,
                ingested_at,
            )
            for x in orders
        ],
        "rates": [
            (
                x.fecha,
                x.currency,
                x.rate_to_mxn,
                "suspected_truncation"
                if x.currency == "EUR" and x.rate_to_mxn == Decimal("22.0")
                else "normal",
                run_id,
                ingested_at,
            )
            for x in rates
        ],
    }
    if engine == "pardox":
        data["sales"] = build_pos_sales_pardox(paths[0], run_id, ingested_at)
        for name in ("stores", "products", "mappings", "snapshots", "orders", "rates"):
            data[name] = []
    changed_paths = (
        paths
        if force
        else [path for path in paths if previous.get(source_names[path]) != hashes_before[path]]
    )
    table_modes = {name: "skipped" for name in TABLES}
    source_modes = {source_names[path]: "skipped" for path in paths}
    source_to_tables = {
        source_names[paths[0]]: ["sales"],
        source_names[paths[1]]: ["stores", "products", "mappings", "snapshots"],
        source_names[paths[2]]: ["orders"],
        source_names[paths[3]]: ["rates"],
    }
    with connect() as conn, conn.cursor() as cur:
        for path in changed_paths:
            names = source_to_tables[source_names[path]]
            for name in names:
                if force or name in {"stores", "products", "mappings"}:
                    table_modes[name] = "full"
                    continue
                table, key_columns = TABLES[name]
                cur.execute(f"SELECT {key_columns.strip('()')}, row_hash FROM {table}")
                existing = {
                    (row[:-1] if len(row) > 2 else row[0]): row[-1] for row in cur.fetchall()
                }
                incoming = {business_key(name, row): row_hash(row[:-2]) for row in data[name]}
                table_modes[name] = (
                    "incremental"
                    if set(existing).issubset(incoming)
                    and all(existing[key] == incoming[key] for key in existing)
                    else "full"
                )
            modes = {table_modes[name] for name in names} - {"skipped"}
            source_modes[source_names[path]] = "incremental" if modes == {"incremental"} else "full"
    if engine == "pardox":
        table_modes = {name: "full" for name in TABLES}
        source_modes = {source_names[path]: "full" for path in paths}
    for manifest in manifests:
        manifest.load_mode = source_modes[manifest.source_file]
    load(
        run_id,
        manifests,
        q_sales + q_stores + q_mappings + q_products + q_snapshots + q_orders + q_rates,
        data,
        paths,
        hashes_before,
        table_modes,
        target_schema="silver_pardox" if engine == "pardox" else "silver",
    )
    payload = {"run_id": str(run_id), "manifests": [m.model_dump(mode="json") for m in manifests]}
    (MANIFEST_DIR / f"{run_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    result = {
        "run_id": str(run_id),
        "load_mode": source_modes,
        "engine": engine,
        "engine_fallback": engine_metadata.fallbacks,
        "manifests": payload["manifests"],
    }
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    with (log_dir / "engine_runs.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(json.dumps(result, ensure_ascii=False))
    return json.dumps(source_modes, sort_keys=True)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="force a full Silver load")
    parser.add_argument("--engine", choices=("polars", "pardox"), default="polars")
    args = parser.parse_args()
    run_id = uuid4()
    started = now()
    try:
        _run(run_id, started, force=args.force, engine=args.engine)
    except Exception as error:
        record_failed(run_id, started, error)
        raise


if __name__ == "__main__":
    main()
