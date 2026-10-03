with by_store as (
    select product_id, sum(quantity) as units_sold
    from {{ ref('fct_sales') }}
    where source_name = 'POS'
      and sale_date between ({{ var('anchor_date') }}::date - interval '6 months' + interval '1 day')
      and {{ var('anchor_date') }}::date
      and match_method <> 'unmatched'
    group by product_id
), network as (
    select product_id, units_sold
    from {{ ref('mart_inventory_turnover_top10') }}
)
select b.product_id
from by_store b
join network n using (product_id)
where b.units_sold <> n.units_sold
