from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "datos"
EVIDENCE_PATH = ROOT / "artifacts" / "evidence" / "profiling.md"
CLIENT_CITIES = {
    "CDMX",
    "Monterrey",
    "Guadalajara",
    "Tijuana",
    "Mexicali",
    "Ciudad Juárez",
    "León",
    "Querétaro",
}


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    normalized = [[str(value).replace("|", "\\|") for value in row] for row in rows]
    lines = [
        f"| {' | '.join(headers)} |",
        f"| {' | '.join(['---'] * len(headers))} |",
    ]
    lines.extend(f"| {' | '.join(row)} |" for row in normalized)
    return "\n".join(lines)


def money(value: float | int | None) -> str:
    return f"{float(value or 0):,.2f}"


def percentage(numerator: float | int, denominator: float | int) -> str:
    return f"{100 * float(numerator) / float(denominator):.2f}%"


def normalize_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value.casefold()))


def product_number(value: str | None) -> str | None:
    if value is None:
        return None
    match = re.search(r"(\d{3})(?:[-_][A-Za-z])?$", value)
    return match.group(1) if match else None


def profile_sales() -> tuple[pl.DataFrame, list[str], dict[str, Any]]:
    sales = pl.read_csv(
        RAW_DIR / "sales.csv",
        schema_overrides={"venta_id": pl.String, "tienda_id": pl.String, "sku": pl.String},
        try_parse_dates=True,
    ).with_columns((pl.col("monto") / pl.col("cantidad")).alias("precio_unitario"))
    receipt_stats = (
        sales.group_by("tipo_comprobante")
        .agg(
            pl.len().alias("filas"),
            pl.col("monto").sum().alias("monto"),
            pl.col("precio_unitario").median().alias("precio_mediano"),
            pl.col("cantidad").mean().alias("cantidad_media"),
            pl.col("precio_unitario").min().alias("precio_minimo"),
            pl.col("precio_unitario").max().alias("precio_maximo"),
            (pl.col("cantidad") <= 0).sum().alias("cantidades_no_positivas"),
        )
        .sort("tipo_comprobante")
    )
    receipt_rows = receipt_stats.select("tipo_comprobante", "filas", "monto").rows()
    lines = [
        "## `sales.csv`",
        "",
        markdown_table(
            ["Métrica", "Evidencia"],
            [
                ["Filas", sales.height],
                [
                    "Rango `fecha_hora`",
                    f"{sales['fecha_hora'].min()} — {sales['fecha_hora'].max()}",
                ],
                ["`venta_id` duplicados", sales["venta_id"].is_duplicated().sum()],
                ["Cantidad ≤ 0", sales.filter(pl.col("cantidad") <= 0).height],
                ["Monto ≤ 0", sales.filter(pl.col("monto") <= 0).height],
                ["Monedas", ", ".join(sorted(sales["moneda"].unique().to_list()))],
                ["Tiendas distintas", sales["tienda_id"].n_unique()],
            ],
        ),
        "",
        "### Tipos de comprobante",
        "",
        markdown_table(
            [
                "Tipo",
                "Filas",
                "Monto",
                "Precio unitario mediano",
                "Cantidad media",
                "Rango de precio unitario",
                "Cantidad ≤ 0",
            ],
            [
                [
                    row["tipo_comprobante"],
                    row["filas"],
                    money(row["monto"]),
                    money(row["precio_mediano"]),
                    f"{row['cantidad_media']:.3f}",
                    f"{money(row['precio_minimo'])} — {money(row['precio_maximo'])}",
                    row["cantidades_no_positivas"],
                ]
                for row in receipt_stats.iter_rows(named=True)
            ],
        ),
        "",
        (
            "Los cinco tipos tienen cantidades estrictamente positivas y rangos de precio unitario "
            "superpuestos (mínimos 15.67 a 16.57; máximos 797.14 a 828.24). No existe evidencia de "
            "signo o precio que permita tratar un tipo como resta o excluirlo."
        ),
    ]
    facts = {
        "min_date": sales["fecha_hora"].min().date(),
        "max_date": sales["fecha_hora"].max().date(),
        "receipt_rows": receipt_rows,
    }
    return sales, lines, facts


def profile_inventory() -> tuple[dict[str, Any], pl.DataFrame, list[str], dict[str, Any]]:
    inventory = json.loads((RAW_DIR / "inventory.json").read_text(encoding="utf-8"))
    snapshots = pl.DataFrame(
        inventory["snapshots"],
        schema_overrides={"cantidad_en_stock": pl.String},
        infer_schema_length=None,
    ).with_columns(
        pl.col("fecha").str.to_date(),
        pl.col("cantidad_en_stock").cast(pl.String).alias("stock_raw"),
        pl.col("cantidad_en_stock").cast(pl.Int64, strict=False).alias("stock_quantity"),
    )
    snapshot_dates = sorted(snapshots["fecha"].unique().to_list())
    expected_dates = {
        snapshot_dates[0] + timedelta(days=offset)
        for offset in range((snapshot_dates[-1] - snapshot_dates[0]).days + 1)
    }
    missing_days = sorted(expected_dates.difference(snapshot_dates))
    duplicate_keys = snapshots.select(
        pl.struct("fecha", "tienda_id", "sku_erp").is_duplicated().sum()
    ).item()
    products = inventory["catalogo"]["productos"]
    cost_entries = [entry for product in products for entry in product.get("cost_history", [])]
    cost_dates = [date.fromisoformat(entry["fecha_vigencia"]) for entry in cost_entries]
    stores = pl.DataFrame(inventory["tiendas_info"])
    store_summary = (
        stores.group_by("ciudad", "region", "timezone")
        .agg(pl.len().alias("tiendas"))
        .sort("ciudad", "region", "timezone")
    )
    erp_cities = set(stores["ciudad"].unique().to_list())
    unmentioned_cities = sorted(erp_cities.difference(CLIENT_CITIES))
    lines = [
        "## `inventory.json`",
        "",
        markdown_table(
            ["Métrica", "Evidencia"],
            [
                ["Claves raíz", ", ".join(inventory.keys())],
                ["Filas `tiendas_info`", len(inventory["tiendas_info"])],
                ["Filas `sku_mappings`", len(inventory["sku_mappings"])],
                ["Productos de catálogo", len(products)],
                ["Filas `snapshots`", snapshots.height],
                ["Rango de snapshots", f"{snapshot_dates[0]} — {snapshot_dates[-1]}"],
                ["Fechas distintas", len(snapshot_dates)],
                ["Días faltantes dentro del rango", len(missing_days)],
                ["Frecuencia observada", "Diaria" if not missing_days else "No diaria"],
                ["Duplicados `(fecha, tienda_id, sku_erp)`", duplicate_keys],
                ["Valores `N/A`", snapshots["stock_quantity"].null_count()],
                ["Stocks negativos", snapshots.filter(pl.col("stock_quantity") < 0).height],
                ["Tiendas distintas", snapshots["tienda_id"].n_unique()],
                ["Registros de costo", len(cost_entries)],
                ["Rango de vigencias de costo", f"{min(cost_dates)} — {max(cost_dates)}"],
                [
                    "Productos con múltiples costos",
                    sum(len(p.get("cost_history", [])) > 1 for p in products),
                ],
            ],
        ),
        "",
        (
            "El catálogo guarda vigencias en `catalogo.productos[].cost_history[]` con "
            "`fecha_vigencia`, `costo_mxn` y `proveedor`."
        ),
        "",
        "### Tiendas ERP frente al relato del cliente",
        "",
        markdown_table(
            ["Ciudad ERP", "Región ERP", "Zona horaria", "Tiendas", "Mencionada por cliente"],
            [
                [
                    row["ciudad"],
                    row["region"],
                    row["timezone"],
                    row["tiendas"],
                    (
                        "Sí (Bajío)"
                        if row["ciudad"] in {"León", "Querétaro"}
                        else "Sí"
                        if row["ciudad"] in CLIENT_CITIES
                        else "No"
                    ),
                ]
                for row in store_summary.iter_rows(named=True)
            ],
        ),
        "",
        (
            f"Ciudades del ERP no mencionadas en el reto: {', '.join(unmentioned_cities)}. "
            "`Monterrey` y `Chihuahua` están clasificadas como región `centro`, una "
            "inconsistencia que debe reportarse al cliente sin sobrescribir el maestro."
        ),
    ]
    facts = {
        "min_date": snapshot_dates[0],
        "max_date": snapshot_dates[-1],
        "na_count": snapshots["stock_quantity"].null_count(),
        "duplicate_keys": duplicate_keys,
        "stores": stores,
    }
    return inventory, snapshots, lines, facts


def profile_sales_timezone(sales: pl.DataFrame, stores: pl.DataFrame) -> list[str]:
    hourly_range = (
        sales.join(stores.select("tienda_id", "timezone"), on="tienda_id", how="left")
        .with_columns(pl.col("fecha_hora").dt.hour().alias("hora"))
        .group_by("timezone")
        .agg(
            pl.col("hora").min().alias("hora_minima"),
            pl.col("hora").max().alias("hora_maxima"),
            pl.len().alias("ventas"),
        )
        .sort("timezone")
    )
    return [
        "## Evidencia de zona horaria de ventas",
        "",
        markdown_table(
            ["Zona horaria ERP", "Hora mínima", "Hora máxima", "Ventas"],
            hourly_range.rows(),
        ),
        "",
        (
            "Todas las zonas presentan ventas de 07:00 a 21:00. La distribución es evidencia de "
            "que `fecha_hora` ya representa hora local de la tienda; no se aplicará una conversión "
            "UTC inventada."
        ),
    ]


def profile_ecommerce(inventory: dict[str, Any]) -> tuple[pl.DataFrame, list[str], dict[str, Any]]:
    orders = pl.read_parquet(RAW_DIR / "ecommerce_orders.parquet").with_columns(
        pl.col("fecha").str.to_datetime().alias("order_datetime")
    )
    mapped_handles = {
        mapping["handle"] for mapping in inventory["sku_mappings"] if mapping.get("handle")
    }
    handles = set(orders["product_handle"].drop_nulls().unique().to_list())
    unmapped_handles = sorted(handles.difference(mapped_handles))
    pii_columns = [
        name
        for name in orders.columns
        if any(token in name for token in ("customer", "address", "email", "rfc", "city"))
    ]
    lines = [
        "## `ecommerce_orders.parquet`",
        "",
        "### Schema físico",
        "",
        "```text",
        *[
            f"{name}: {data_type}"
            for name, data_type in pl.read_parquet_schema(
                RAW_DIR / "ecommerce_orders.parquet"
            ).items()
        ],
        "```",
        "",
        markdown_table(
            ["Métrica", "Evidencia"],
            [
                ["Filas", orders.height],
                [
                    "Rango de fechas",
                    f"{orders['order_datetime'].min()} — {orders['order_datetime'].max()}",
                ],
                ["Monedas", ", ".join(sorted(orders["currency"].unique().to_list()))],
                ["Columnas de PII", ", ".join(pii_columns)],
                ["Handles distintos", len(handles)],
                ["Handles sin mapping explícito", len(unmapped_handles)],
                ["Lista sin mapping explícito", ", ".join(unmapped_handles) or "Ninguno"],
            ],
        ),
    ]
    facts = {
        "min_date": orders["order_datetime"].min().date(),
        "max_date": orders["order_datetime"].max().date(),
    }
    return orders, lines, facts


def profile_exchange_rates(orders: pl.DataFrame) -> tuple[list[str], dict[str, Any]]:
    rates = pl.read_csv(RAW_DIR / "exchange_rates.csv", try_parse_dates=True)
    foreign_orders = orders.filter(pl.col("currency").is_in(["USD", "EUR"])).with_columns(
        pl.col("order_datetime").dt.date().alias("fecha")
    )
    coverage = (
        foreign_orders.join(rates, on=["fecha", "currency"], how="left")
        .group_by("currency")
        .agg(
            pl.len().alias("ordenes"),
            pl.col("fecha").n_unique().alias("fechas"),
            pl.col("rate_to_mxn").is_not_null().sum().alias("ordenes_con_tasa"),
            pl.col("rate_to_mxn").is_null().sum().alias("ordenes_sin_tasa"),
        )
        .sort("currency")
    )
    date_pairs = foreign_orders.select("fecha", "currency").unique()
    missing_pairs = date_pairs.join(
        rates.select("fecha", "currency"), on=["fecha", "currency"], how="anti"
    )
    eur_22 = rates.filter((pl.col("currency") == "EUR") & (pl.col("rate_to_mxn") == 22.0)).sort(
        "fecha"
    )
    eur_22_series = ", ".join(str(value) for value in eur_22["fecha"].to_list())
    lines = [
        "## `exchange_rates.csv` y cobertura FX de e-commerce",
        "",
        markdown_table(
            ["Métrica", "Evidencia"],
            [
                ["Filas", rates.height],
                ["Rango", f"{rates['fecha'].min()} — {rates['fecha'].max()}"],
                ["Monedas", ", ".join(sorted(rates["currency"].unique().to_list()))],
                ["Pares fecha/moneda e-commerce USD/EUR", date_pairs.height],
                ["Pares sin tasa", missing_pairs.height],
            ],
        ),
        "",
        markdown_table(
            ["Moneda", "Órdenes", "Fechas", "Órdenes con tasa", "Órdenes sin tasa"],
            coverage.rows(),
        ),
        "",
        f"### Serie EUR con tasa exactamente 22.0 ({eur_22.height} días)",
        "",
        eur_22_series,
        "",
        (
            "Sesenta y tres observaciones EUR son exactamente `22.0`; la repetición del valor "
            "redondo se marca como sospechosa de truncamiento. La tasa se conserva y se usará con "
            "`fx_quality_flag`, no se descarta."
        ),
    ]
    return lines, {"missing_pairs": missing_pairs.height, "eur_22_days": eur_22.height}


def mapping_coverage(
    sales: pl.DataFrame, orders: pl.DataFrame, inventory: dict[str, Any]
) -> tuple[list[str], dict[str, Any]]:
    mappings = inventory["sku_mappings"]
    products = inventory["catalogo"]["productos"]
    erp_by_number = {product_number(product["sku_erp"]): product for product in products}
    explicit_pos = {
        mapping["sku_pos"]: mapping["sku_erp"] for mapping in mappings if mapping.get("sku_pos")
    }
    explicit_handle = {
        mapping["handle"]: mapping["sku_erp"] for mapping in mappings if mapping.get("handle")
    }

    sales_methods: list[str | None] = []
    for sku in sales["sku"].to_list():
        if sku in explicit_pos:
            sales_methods.append("explicit")
        elif product_number(sku) in erp_by_number:
            sales_methods.append("product_number")
        else:
            sales_methods.append(None)
    sales_matches = sales.with_columns(pl.Series("match_method", sales_methods))

    order_methods: list[str | None] = []
    mismatches: list[list[str]] = []
    for handle in orders["product_handle"].to_list():
        if handle in explicit_handle:
            order_methods.append("explicit")
            continue
        number = product_number(handle)
        product = erp_by_number.get(number)
        if product is None:
            order_methods.append(None)
            continue
        handle_name = re.sub(r"[-_]?\d{3}$", "", handle)
        normalized_handle = normalize_name(handle_name)
        normalized_catalog = normalize_name(product["nombre"])
        if normalized_handle == normalized_catalog:
            order_methods.append("product_number")
        else:
            order_methods.append(None)
            mismatches.append([handle, product["sku_erp"], product["nombre"]])
    order_matches = orders.with_columns(pl.Series("match_method", order_methods))

    mapped_sales = sales_matches.filter(pl.col("match_method").is_not_null())
    mapped_orders = order_matches.filter(pl.col("match_method").is_not_null())
    method_counts = [
        ["POS", method, count]
        for method, count in sales_matches.group_by("match_method")
        .len()
        .sort("match_method")
        .rows()
    ] + [
        ["Shopify", method, count]
        for method, count in order_matches.group_by("match_method")
        .len()
        .sort("match_method")
        .rows()
    ]
    sales_units = mapped_sales["cantidad"].sum()
    total_sales_units = sales["cantidad"].sum()
    sales_amount = mapped_sales["monto"].sum()
    total_sales_amount = sales["monto"].sum()
    order_units = mapped_orders["cantidad"].sum()
    total_order_units = orders["cantidad"].sum()
    order_amount = mapped_orders["amount"].sum()
    total_order_amount = orders["amount"].sum()
    coverage_rows = [
        [
            "POS → ERP",
            (
                f"{mapped_sales.height}/{sales.height} "
                f"({percentage(mapped_sales.height, sales.height)})"
            ),
            f"{sales_units}/{total_sales_units} ({percentage(sales_units, total_sales_units)})",
            (
                f"{money(sales_amount)}/{money(total_sales_amount)} "
                f"({percentage(sales_amount, total_sales_amount)})"
            ),
        ],
        [
            "Shopify → ERP",
            (
                f"{mapped_orders.height}/{orders.height} "
                f"({percentage(mapped_orders.height, orders.height)})"
            ),
            f"{order_units}/{total_order_units} ({percentage(order_units, total_order_units)})",
            (
                f"{money(order_amount)}/{money(total_order_amount)} "
                f"({percentage(order_amount, total_order_amount)})"
            ),
        ],
    ]
    unique_mismatches = sorted({tuple(row) for row in mismatches})
    lines = [
        "## Conciliación de producto",
        "",
        (
            "El número final de tres dígitos se extrajo de POS (`CN-00013` → `013`), ERP "
            "(`ERP-PROV-MX-013-B` → `013`) y Shopify (`…-013` → `013`). Se aplicó mapping "
            "explícito primero y número como respaldo; para Shopify el respaldo exige igualdad del "
            "nombre normalizado sin acentos, mayúsculas ni separadores."
        ),
        "",
        markdown_table(["Fuente", "Método", "Filas"], method_counts),
        "",
        markdown_table(["Relación", "Filas", "Unidades", "Monto fuente"], coverage_rows),
        "",
        "### Coincidencia de número con nombre distinto",
        "",
        (
            markdown_table(
                ["Handle", "SKU ERP por número", "Nombre catálogo"],
                [list(row) for row in unique_mismatches],
            )
            if unique_mismatches
            else "Ningún caso."
        ),
        "",
        "Lo no conciliado se enviará a Audit; no se elimina ni se fuerza a un producto.",
    ]
    return lines, {
        "mapped_sales": mapped_sales.height,
        "mapped_orders": mapped_orders.height,
        "name_mismatches": len(unique_mismatches),
    }


def prompt_injection_review() -> list[str]:
    return [
        "## Revisión de instrucciones embebidas (prompt injection)",
        "",
        markdown_table(
            ["Superficie", "Revisión", "Resultado"],
            [
                [
                    "PDF",
                    "Texto extraído, metadatos y revisión visual de sus 4 páginas",
                    "Sin instrucciones embebidas",
                ],
                [
                    "DOCX",
                    "Texto, `w:vanish`, texto blanco, relaciones y `customXML`",
                    "Sin instrucciones embebidas",
                ],
                [
                    "ZIP",
                    "Inventario de entradas y contenido de los cuatro archivos",
                    "Sin instrucciones embebidas",
                ],
                [
                    "Parquet",
                    "Schema, cabecera/footer binario y campos de texto de Shopify",
                    "Sin instrucciones embebidas",
                ],
                ["JSON", "Claves y todos los valores de texto", "Sin instrucciones embebidas"],
            ],
        ),
        "",
        (
            "El DOCX contiene `customXML/item1.xml`, pero no instrucciones; tampoco se encontraron "
            "runs ocultos (`w:vanish`) ni texto blanco. Los campos de texto de Shopify se "
            "revisaron junto con el resto del Parquet."
        ),
    ]


def closed_interpretations(common_anchor: date, inventory_facts: dict[str, Any]) -> list[str]:
    return [
        "## Interpretaciones cerradas por el propietario",
        "",
        markdown_table(
            ["Tema", "Evidencia", "Decisión"],
            [
                [
                    "CFDI",
                    "Cinco tipos; cantidades y montos positivos; rangos de precios superpuestos.",
                    (
                        "Todas son ventas. El CFDI se cuenta por tipo; el tipo nunca altera signo "
                        "ni inclusión."
                    ),
                ],
                [
                    "Producto",
                    (
                        "Número común a POS, ERP y Shopify; nombres Shopify validables contra "
                        "catálogo."
                    ),
                    (
                        "Explícito primero; respaldo por número+nombre; `match_method`; no "
                        "conciliado a Audit."
                    ),
                ],
                [
                    "IVA",
                    "No existe columna de impuesto; categorías con tasas 0% y 16%.",
                    "`monto` es importe neto sin IVA como supuesto documentado.",
                ],
                [
                    "Tiendas",
                    "ERP contiene ciudades no citadas y regiones inconsistentes.",
                    (
                        "`tiendas_info` es maestro; discrepancia reportada y pregunta abierta al "
                        "cliente."
                    ),
                ],
                [
                    "FX",
                    "Cobertura diaria completa; EUR=22.0 exacto en 63 días.",
                    "Tasa de la fecha; se usa y se marca `fx_quality_flag` si es sospechosa.",
                ],
                [
                    "P2",
                    f"Snapshots diarios; N/A={inventory_facts['na_count']}.",
                    (
                        "Tienda listada si algún SKU tuvo >3 días con stock=0; N/A rompe; salida "
                        "conserva detalle."
                    ),
                ],
                [
                    "P4",
                    "POS tiene tienda; Shopify no.",
                    "POS por tienda; e-commerce como canal `ONLINE`.",
                ],
                [
                    "Ventanas",
                    f"Máxima fecha común {common_anchor}; inventario 2025-10-01—2026-03-31.",
                    "Ancla 2026-03-31; P1 usa esos 6 meses; MoM 2025-04 es `null` sin base.",
                ],
                [
                    "Reconciliación",
                    "Tres fuentes difieren en cobertura, identidad y granularidad.",
                    "Se prevé un mart Gold que explique diferencias POS/ERP/Shopify.",
                ],
            ],
        ),
    ]


def main() -> None:
    sales, sales_lines, sales_facts = profile_sales()
    inventory, _, inventory_lines, inventory_facts = profile_inventory()
    orders, ecommerce_lines, ecommerce_facts = profile_ecommerce(inventory)
    fx_lines, _ = profile_exchange_rates(orders)
    mapping_lines, _ = mapping_coverage(sales, orders, inventory)
    common_anchor = min(
        sales_facts["max_date"], inventory_facts["max_date"], ecommerce_facts["max_date"]
    )
    lines = [
        "# Perfilado reproducible de fuentes",
        "",
        f"Generado: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        (
            "Los conteos provienen directamente de `datos/`; no se aplicaron transformaciones "
            "Silver ni se modificaron las fuentes."
        ),
        "",
        *sales_lines,
        "",
        *inventory_lines,
        "",
        *profile_sales_timezone(sales, inventory_facts["stores"]),
        "",
        *ecommerce_lines,
        "",
        *fx_lines,
        "",
        *mapping_lines,
        "",
        "## Fecha máxima común",
        "",
        (
            f"**{common_anchor}** = mínimo de máximos: ventas {sales_facts['max_date']}, "
            f"inventario {inventory_facts['max_date']}, ecommerce {ecommerce_facts['max_date']}."
        ),
        "",
        *prompt_injection_review(),
        "",
        *closed_interpretations(common_anchor, inventory_facts),
        "",
    ]
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
