# Respuestas certificadas

Generado desde marts dbt en analytics.

## p1_inventory_turnover_top10

Periodo: 2025-10-01—2026-03-31
Filas exportadas: 10

```sql
select * from analytics.mart_inventory_turnover_top10 order by ranking
```

## p2_stockouts_over_3_days

Periodo: 2026-01-01—2026-03-31
Filas exportadas: 3

```sql
select * from analytics.mart_stockouts_over_3_days order by tienda_id, product_id, start_date
```

## p3_monthly_channel_growth

Periodo: 2025-04-01—2026-03-31
Filas exportadas: 492

```sql
select * from analytics.mart_monthly_channel_growth order by channel, month_start
```

## p3_monthly_channel_type_growth

Periodo: 2025-04-01—2026-03-31
Filas exportadas: 24

```sql
select * from analytics.mart_monthly_channel_type_growth order by channel_type, month_start
```

## p4_negative_margin_products

Periodo: 2025-04-01—2026-03-31
Filas exportadas: 120

```sql
select * from analytics.mart_negative_margin_products order by gross_margin_mxn
```
