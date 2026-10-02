select day::date as date_day
from generate_series({{ var('anchor_date') }}::date - interval '18 months', {{ var('anchor_date') }}::date, interval '1 day') day
