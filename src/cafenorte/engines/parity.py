"""Parity checks for the SPEC-003 POS-only route."""


def check_parity(conn) -> list[str]:
    differences: list[str] = []
    columns = (
        "venta_id, fecha_hora_normalizada, tienda_id, sku, product_number, "
        "cantidad, monto, moneda, tipo_comprobante"
    )
    with conn.cursor() as cur:
        for left, right in (("silver", "silver_pardox"), ("silver_pardox", "silver")):
            cur.execute(
                f"SELECT venta_id FROM (SELECT {columns} FROM {left}.pos_sales "
                f"EXCEPT SELECT {columns} FROM {right}.pos_sales) d ORDER BY venta_id"
            )
            differences.extend(str(row[0]) for row in cur.fetchall())
        totals = []
        for schema in ("silver", "silver_pardox"):
            cur.execute(f"SELECT count(*), sum(cantidad), sum(monto) FROM {schema}.pos_sales")
            totals.append(cur.fetchone())
        if totals[0] != totals[1]:
            differences.append("aggregate_totals")
        for expression, label in (
            ("tienda_id, date_trunc('month', fecha_hora_normalizada)", "store_month"),
            ("tipo_comprobante", "tipo_comprobante"),
        ):
            queries = [
                f"SELECT {expression}, count(*), sum(cantidad), sum(monto) "
                f"FROM {schema}.pos_sales GROUP BY 1, 2"
                if label == "store_month"
                else f"SELECT {expression}, count(*), sum(cantidad), sum(monto) "
                f"FROM {schema}.pos_sales GROUP BY 1"
                for schema in ("silver", "silver_pardox")
            ]
            values = []
            for query in queries:
                cur.execute(query)
                values.append(sorted(cur.fetchall(), key=str))
            if values[0] != values[1]:
                differences.append(label)
    row_differences = sorted({value for value in differences if value.startswith("V")})
    return row_differences if row_differences else sorted(set(differences))
