select * from {{ ref('fct_inventory_daily') }}
where stock_raw_value = 'N/A' and stock_quantity = 0
