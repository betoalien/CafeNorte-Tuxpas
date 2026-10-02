# Respuestas Bloque C

Generado desde marts dbt en analytics.

## p1_inventory_turnover_top10

Filas exportadas: 10

```sql
select * from analytics.mart_inventory_turnover_top10 order by ranking
```

## p2_stockouts_over_3_days

Filas exportadas: 3

```sql
select * from analytics.mart_stockouts_over_3_days order by tienda_id, product_id, start_date
```

## p3_monthly_channel_growth

Filas exportadas: 492

```sql
select * from analytics.mart_monthly_channel_growth order by channel, month_start
```

## p4_negative_margin_products

Filas exportadas: 120

```sql
select * from analytics.mart_negative_margin_products order by gross_margin_mxn
```
