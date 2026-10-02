with violations as (
    select product_id, inventory_turnover_ratio
    from {{ ref('mart_inventory_turnover_top10') }}
    where inventory_turnover_ratio < 0.1
       or inventory_turnover_ratio > 10
)
select * from violations
