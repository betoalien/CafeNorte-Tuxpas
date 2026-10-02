"""Read-only Bronze ingestion and transactional Polars/Pydantic Silver load."""

import csv
import hashlib
import json
import os
import re
from collections.abc import Callable
from datetime import UTC, datetime
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

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datos"
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
    match = re.search(r"(\d{3})$", value)
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
    path: Path, run_id: UUID, started: datetime, input_count: int, accepted: int, rejected: int
) -> Manifest:
    before = sha256(path)
    after = sha256(path)
    if before != after:
        raise RuntimeError(f"Source changed while reading: {path}")
    return Manifest(
        run_id=run_id,
        source_file=str(path.relative_to(ROOT)),
        sha256_before=before,
        sha256_after=after,
        size_bytes=path.stat().st_size,
        input_count=input_count,
        accepted_count=accepted,
        rejected_count=rejected,
        contract_version=CONTRACT_VERSION,
        started_at=started,
        completed_at=now(),
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
  error_message text
);
CREATE TABLE IF NOT EXISTS audit.ingestion_manifest (
  run_id uuid NOT NULL, source_file text NOT NULL, sha256_before text NOT NULL,
  sha256_after text NOT NULL, size_bytes bigint NOT NULL, input_count bigint NOT NULL,
  accepted_count bigint NOT NULL, rejected_count bigint NOT NULL, contract_version text NOT NULL,
  started_at timestamptz NOT NULL, completed_at timestamptz NOT NULL,
  PRIMARY KEY (run_id, source_file)
);
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
  run_id uuid NOT NULL, ingested_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS silver.stores (
  tienda_id text PRIMARY KEY, ciudad text NOT NULL, region text NOT NULL, timezone text NOT NULL,
  run_id uuid NOT NULL, ingested_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS silver.products (
  sku_erp text PRIMARY KEY, product_number text, nombre text NOT NULL, categoria text NOT NULL,
  cost_history jsonb NOT NULL, run_id uuid NOT NULL, ingested_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS silver.sku_mappings (
  sku_pos text PRIMARY KEY, sku_erp text, handle text, run_id uuid NOT NULL,
  ingested_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS silver.inventory_snapshots (
  fecha date NOT NULL, tienda_id text NOT NULL, sku_erp text NOT NULL, stock_quantity integer,
  stock_raw_value text NOT NULL, quality_status text NOT NULL, quality_reason text NOT NULL,
  run_id uuid NOT NULL, ingested_at timestamptz NOT NULL, PRIMARY KEY (fecha, tienda_id, sku_erp)
);
CREATE TABLE IF NOT EXISTS silver.ecommerce_orders (
  order_id text PRIMARY KEY, fecha timestamp NOT NULL, product_handle text NOT NULL,
  product_number text,
  handle_name_normalized text NOT NULL, cantidad bigint NOT NULL, amount numeric(18,2) NOT NULL,
  currency text NOT NULL, run_id uuid NOT NULL, ingested_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS silver.exchange_rates (
  fecha date NOT NULL, currency text NOT NULL, rate_to_mxn numeric(18,6) NOT NULL,
  fx_quality_flag text NOT NULL, run_id uuid NOT NULL, ingested_at timestamptz NOT NULL,
  PRIMARY KEY (fecha, currency)
);
"""


def insert_rows(cur: psycopg.Cursor, sql: str, rows: list[tuple[Any, ...]]) -> None:
    if rows:
        cur.executemany(sql, rows)


def load(
    run_id: UUID,
    manifests: list[Manifest],
    quarantines: list[QuarantineRecord],
    data: dict[str, Any],
) -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        cur.execute("DELETE FROM silver.pos_sales")
        cur.execute("DELETE FROM silver.stores")
        cur.execute("DELETE FROM silver.products")
        cur.execute("DELETE FROM silver.sku_mappings")
        cur.execute("DELETE FROM silver.inventory_snapshots")
        cur.execute("DELETE FROM silver.ecommerce_orders")
        cur.execute("DELETE FROM silver.exchange_rates")
        cur.execute("DELETE FROM audit.quarantine")
        for table in (
            "pos_sales",
            "stores",
            "products",
            "sku_mappings",
            "inventory_snapshots",
            "ecommerce_orders",
            "exchange_rates",
        ):
            cur.execute(f"ALTER TABLE silver.{table} DISABLE TRIGGER ALL")
        insert_rows(
            cur,
            "INSERT INTO silver.pos_sales VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            data["sales"],
        )
        insert_rows(cur, "INSERT INTO silver.stores VALUES (%s,%s,%s,%s,%s,%s)", data["stores"])
        insert_rows(
            cur, "INSERT INTO silver.products VALUES (%s,%s,%s,%s,%s,%s,%s)", data["products"]
        )
        insert_rows(
            cur, "INSERT INTO silver.sku_mappings VALUES (%s,%s,%s,%s,%s)", data["mappings"]
        )
        insert_rows(
            cur,
            "INSERT INTO silver.inventory_snapshots VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            data["snapshots"],
        )
        insert_rows(
            cur,
            "INSERT INTO silver.ecommerce_orders VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            data["orders"],
        )
        insert_rows(
            cur, "INSERT INTO silver.exchange_rates VALUES (%s,%s,%s,%s,%s,%s)", data["rates"]
        )
        for table in (
            "pos_sales",
            "stores",
            "products",
            "sku_mappings",
            "inventory_snapshots",
            "ecommerce_orders",
            "exchange_rates",
        ):
            cur.execute(f"ALTER TABLE silver.{table} ENABLE TRIGGER ALL")
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
            "INSERT INTO audit.ingestion_manifest VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            [tuple(m.model_dump().values()) for m in manifests],
        )
        total_input = sum(m.input_count for m in manifests)
        total_accepted = sum(m.accepted_count for m in manifests)
        total_rejected = sum(m.rejected_count for m in manifests)
        cur.execute(
            "INSERT INTO audit.run_log VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                run_id,
                manifests[0].started_at,
                now(),
                "succeeded",
                total_input,
                total_accepted,
                total_rejected,
                None,
            ),
        )


def main() -> None:
    run_id = uuid4()
    started = now()
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
    sales_rows = read_csv(paths[0])
    for row in sales_rows:
        row["cantidad"] = int(row["cantidad"])
        row["monto"] = float(row["monto"])
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
    orders, q_orders = parse_records(
        "ecommerce_orders.parquet",
        orders_rows,
        EcommerceOrderRecord,
        lambda r: r.get("order_id", ""),
        run_id,
    )
    rate_rows = read_csv(paths[3])
    for row in rate_rows:
        row["rate_to_mxn"] = float(row["rate_to_mxn"])
    rates, q_rates = parse_records(
        "exchange_rates.csv",
        rate_rows,
        ExchangeRateRecord,
        lambda r: f"{r.get('fecha')}|{r.get('currency')}",
        run_id,
    )
    dates = {rate.fecha for rate in rates}
    rates.extend(
        ExchangeRateRecord(fecha=day, currency="MXN", rate_to_mxn=1.0) for day in sorted(dates)
    )
    manifests = [
        source_manifest(paths[0], run_id, started, len(sales_rows), len(sales), len(q_sales)),
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
        ),
        source_manifest(paths[2], run_id, started, len(orders_rows), len(orders), len(q_orders)),
        source_manifest(
            paths[3], run_id, started, len(rate_rows), len(rate_rows) - len(q_rates), len(q_rates)
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
        "snapshots": [
            (
                x.fecha,
                x.tienda_id,
                x.sku_erp,
                None if x.cantidad_en_stock == "N/A" else x.cantidad_en_stock,
                str(x.cantidad_en_stock),
                "unknown" if x.cantidad_en_stock == "N/A" else "valid",
                "N/A means unknown" if x.cantidad_en_stock == "N/A" else "",
                run_id,
                ingested_at,
            )
            for x in unique_snapshots
        ],
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
                if x.currency == "EUR" and x.rate_to_mxn == 22.0
                else "normal",
                run_id,
                ingested_at,
            )
            for x in rates
        ],
    }
    load(
        run_id,
        manifests,
        q_sales + q_stores + q_mappings + q_products + q_snapshots + q_orders + q_rates,
        data,
    )
    payload = {"run_id": str(run_id), "manifests": [m.model_dump(mode="json") for m in manifests]}
    (MANIFEST_DIR / f"{run_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps({"run_id": str(run_id), "manifests": payload["manifests"]}, ensure_ascii=False)
    )


if __name__ == "__main__":
    main()
