select * from {{ ref('stg_pos_sales') }}
where quantity <= 0 or amount_mxn <= 0
