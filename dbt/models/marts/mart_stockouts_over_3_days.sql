with base as (
    select *, lag(fecha) over (partition by tienda_id, product_id order by fecha) as previous_date,
           lag(stock_quantity) over (partition by tienda_id, product_id order by fecha) as previous_stock
    from {{ ref('fct_inventory_daily') }}
    where fecha between '2025-12-31' and '2026-03-31'
), zeroes as (
    select *, case when stock_quantity = 0 and previous_stock = 0
             and fecha = previous_date + 1 then 0 else 1 end as new_group
    from base where stock_quantity = 0
), islands as (
    select *, sum(new_group) over (partition by tienda_id, product_id order by fecha) as island_id
    from zeroes
), grouped as (
    select tienda_id, product_id, min(fecha) as raw_start, max(fecha) as raw_end,
           count(*) as raw_days
    from islands group by tienda_id, product_id, island_id
)
select tienda_id, product_id,
       greatest(raw_start, '2026-01-01'::date) as start_date,
       raw_end as end_date,
       (raw_end - greatest(raw_start, '2026-01-01'::date) + 1) as days,
       raw_start < '2026-01-01'::date as starts_before_window,
       '2026-01-01/2026-03-31'::text as period,
       now() as built_at, 'business_metrics.v1'::text as logic_version
from grouped
where raw_end >= '2026-01-01' and raw_days > 3
