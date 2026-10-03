select tienda_id, product_id
from {{ ref('mart_inventory_turnover_by_store') }}
group by tienda_id, product_id
having count(*) > 1
