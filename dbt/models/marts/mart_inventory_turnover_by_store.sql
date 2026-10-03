with store_inventory as (
    select product_id, tienda_id,
           avg(stock_quantity::numeric) as average_valid_inventory_units
    from {{ ref('fct_inventory_daily') }}
    where fecha between ({{ var('anchor_date') }}::date - interval '6 months' + interval '1 day')
        and {{ var('anchor_date') }}::date
    group by product_id, tienda_id
), sold as (
    select product_id, tienda_id, sum(quantity) as units_sold
    from {{ ref('fct_sales') }}
    where source_name = 'POS'
      and sale_date between ({{ var('anchor_date') }}::date - interval '6 months' + interval '1 day')
      and {{ var('anchor_date') }}::date
      and match_method <> 'unmatched'
    group by product_id, tienda_id
), ranked as (
    select s.tienda_id, s.product_id, s.units_sold,
           i.average_valid_inventory_units,
           s.units_sold / nullif(i.average_valid_inventory_units, 0)
               as inventory_turnover_ratio,
           row_number() over (
               partition by s.tienda_id
               order by s.units_sold / nullif(i.average_valid_inventory_units, 0) desc
           ) as ranking
    from sold s
    join store_inventory i using (product_id, tienda_id)
)
select tienda_id, product_id, units_sold, average_valid_inventory_units,
       inventory_turnover_ratio, ranking,
       ({{ var('anchor_date') }}::date - interval '6 months' + interval '1 day')::date
           || '/' || {{ var('anchor_date') }}::date as period,
       now() as built_at, 'business_metrics.v1'::text as logic_version
from ranked
where ranking <= 10
