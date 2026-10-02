with store_inventory as (
    select product_id, tienda_id,
           avg(stock_quantity::numeric) as store_average_valid_inventory_units,
           count(stock_quantity) as valid_snapshot_count,
           count(*) as total_snapshot_count
    from {{ ref('fct_inventory_daily') }}
    where fecha between '2025-10-01' and '2026-03-31'
    group by product_id, tienda_id
), inventory as (
    select product_id,
           sum(store_average_valid_inventory_units) as average_valid_inventory_units,
           sum(valid_snapshot_count)::numeric / nullif(sum(total_snapshot_count), 0) as coverage
    from store_inventory
    group by product_id
), sold as (
    select product_id, sum(quantity) as units_sold
    from {{ ref('fct_sales') }}
    where source_name = 'POS' and sale_date between '2025-10-01' and '2026-03-31'
      and match_method <> 'unmatched'
    group by product_id
), ranked as (
    select i.product_id, s.units_sold, i.average_valid_inventory_units,
           i.coverage,
           s.units_sold / nullif(i.average_valid_inventory_units, 0) as inventory_turnover_ratio,
           row_number() over (order by s.units_sold / nullif(i.average_valid_inventory_units, 0) desc) as ranking
    from inventory i join sold s using (product_id)
)
select product_id, units_sold, average_valid_inventory_units, coverage,
       inventory_turnover_ratio, ranking, '2025-10-01/2026-03-31'::text as period,
       now() as built_at, 'business_metrics.v1'::text as logic_version
from ranked where ranking <= 10
