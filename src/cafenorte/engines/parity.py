"""Parity checks for the SPEC-003 POS-only route."""


def check_parity(conn) -> list[str]:
    differences: list[str] = []
    with conn.cursor() as cur:
        cur.execute(
            """SELECT COALESCE(p.venta_id, x.venta_id), p.row_hash, x.row_hash, p.monto, x.monto
               FROM silver.pos_sales p FULL JOIN silver_pardox.pos_sales x USING (venta_id)
               WHERE p.row_hash IS DISTINCT FROM x.row_hash
                  OR p.monto IS DISTINCT FROM x.monto
                  OR p.venta_id IS NULL OR x.venta_id IS NULL"""
        )
        differences.extend(str(row[0]) for row in cur.fetchall())
        for sql in (
            "SELECT count(*), sum(cantidad), sum(monto) FROM silver.pos_sales",
            "SELECT count(*), sum(cantidad), sum(monto) FROM silver_pardox.pos_sales",
        ):
            cur.execute(sql)
            if sql.startswith("SELECT count"):
                if "reference" not in locals():
                    reference = cur.fetchone()
                elif cur.fetchone() != reference:
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
    row_differences = [value for value in differences if value.startswith("V")]
    return row_differences if row_differences else differences
