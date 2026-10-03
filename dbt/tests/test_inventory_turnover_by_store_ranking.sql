select *
from {{ ref('mart_inventory_turnover_by_store') }}
where ranking > 10
