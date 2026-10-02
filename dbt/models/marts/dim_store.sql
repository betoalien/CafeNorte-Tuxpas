select tienda_id as store_id, ciudad, region, timezone, now() as built_at,
       'business_metrics.v1'::text as logic_version
from {{ ref('stg_stores') }}
