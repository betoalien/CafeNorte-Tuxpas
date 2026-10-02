select day::date as date_day
from generate_series('2024-10-01'::date, '2026-03-31'::date, interval '1 day') day
