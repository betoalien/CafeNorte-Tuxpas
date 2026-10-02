select date_day, extract(year from date_day)::int as year,
       extract(month from date_day)::int as month,
       date_trunc('month', date_day)::date as month_start,
       now() as built_at, 'business_metrics.v1'::text as logic_version
from {{ ref('int_date_spine') }}
