select sku_erp as product_id, product_number, nombre as product_name, categoria, cost_history,
       now() as built_at, 'business_metrics.v1'::text as logic_version
from {{ ref('stg_products') }}
