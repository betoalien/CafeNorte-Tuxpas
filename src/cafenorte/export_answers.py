"""Export the four certified dbt marts as reviewable CSV answers."""

import csv
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "evidence" / "answers"

QUERIES = {
    "p1_inventory_turnover_top10": "select * from analytics.mart_inventory_turnover_top10 order by ranking",
    "p2_stockouts_over_3_days": "select * from analytics.mart_stockouts_over_3_days order by tienda_id, product_id, start_date",
    "p3_monthly_channel_growth": "select * from analytics.mart_monthly_channel_growth order by channel, month_start",
    "p4_negative_margin_products": "select * from analytics.mart_negative_margin_products order by gross_margin_mxn",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ.get("DBT_USER", "dbt"),
        password=os.environ["DBT_PASSWORD"],
    ) as conn, conn.cursor() as cur:
        summary: list[str] = ["# Respuestas Bloque C", "", "Generado desde marts dbt en analytics.", ""]
        for name, sql in QUERIES.items():
            cur.execute(sql)
            headers = [column.name for column in cur.description]
            rows = cur.fetchall()
            if "built_at" in headers:
                built_at_index = headers.index("built_at")
                headers.pop(built_at_index)
                rows = [tuple(value for index, value in enumerate(row) if index != built_at_index) for row in rows]
            with (OUT / f"{name}.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(headers)
                writer.writerows(rows)
            summary.extend([f"## {name}", "", f"Filas exportadas: {len(rows)}", "", "```sql", sql, "```", ""])
        (OUT / "README.md").write_text("\n".join(summary), encoding="utf-8")


if __name__ == "__main__":
    main()
