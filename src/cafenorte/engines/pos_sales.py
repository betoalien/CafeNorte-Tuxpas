"""Equivalent POS Silver builders for the reference and PardoX engines."""

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import polars as pl

from ..contracts import SalesRecord


def row_hash(values: tuple) -> str:
    return hashlib.sha256(json.dumps(values, default=str, sort_keys=True).encode()).hexdigest()


def _silver_rows(records: list[dict], run_id: UUID, ingested_at: datetime) -> list[tuple]:
    result = []
    for raw in records:
        record = SalesRecord.model_validate(raw)
        values = (
            record.venta_id,
            raw["fecha_hora"],
            record.fecha_hora,
            record.tienda_id,
            record.sku,
            _product_number(record.sku),
            record.cantidad,
            record.monto,
            record.moneda,
            record.tipo_comprobante,
            run_id,
            ingested_at,
        )
        result.append((*values, row_hash(values[:-2])))
    return result


def _product_number(value: str) -> str | None:
    import re

    match = re.search(r"(\d{3})(?:-[A-Za-z])?$", value)
    return match.group(1) if match else None


def build_pos_sales_polars(path: Path, run_id: UUID, ingested_at: datetime) -> list[tuple]:
    frame = pl.read_csv(path)
    records = frame.to_dicts()
    for record in records:
        record["cantidad"] = int(record["cantidad"])
        record["monto"] = Decimal(str(record["monto"]))
    return _silver_rows(records, run_id, ingested_at)


def build_pos_sales_pardox(path: Path, run_id: UUID, ingested_at: datetime) -> list[tuple]:
    import pardox as px

    frame = px.read_csv(str(path))
    frame.cast("cantidad", "Int64")
    frame.cast("monto", "Float64")
    frame.cast("fecha_hora", "Utf8")
    frame.validate_contract({"columns": {"cantidad": {"min": 1}, "monto": {"min": 0}}})
    records = frame.to_dict()
    for record in records:
        record["cantidad"] = int(record["cantidad"])
        record["monto"] = Decimal(str(record["monto"]))
    return _silver_rows(records, run_id, ingested_at)
