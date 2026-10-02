{% macro generate_schema_name(custom_schema_name, node) -%}
  {{ custom_schema_name or target.schema }}
{%- endmacro %}

{% macro latest_successful_run_id() -%}
  (select run_id from {{ source('audit', 'run_log') }}
   where status = 'succeeded' order by started_at desc limit 1)
{%- endmacro %}
