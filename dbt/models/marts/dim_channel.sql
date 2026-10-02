select tienda_id as channel, 'POS'::text as channel_type, now() as built_at,
       'business_metrics.v1'::text as logic_version
from {{ ref('stg_stores') }}
union all
select 'ONLINE', 'ONLINE', now(), 'business_metrics.v1'
