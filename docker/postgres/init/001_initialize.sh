#!/usr/bin/env bash
set -euo pipefail

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_database="$POSTGRES_DB" \
  --set=pipeline_password="$PIPELINE_PASSWORD" \
  --set=dbt_password="$DBT_PASSWORD" \
  --set=superset_ro_password="$SUPERSET_RO_PASSWORD" \
  --set=superset_meta_password="$SUPERSET_META_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE pipeline LOGIN PASSWORD %L', :'pipeline_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'pipeline') \gexec
SELECT format('CREATE ROLE dbt LOGIN PASSWORD %L', :'dbt_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'dbt') \gexec
SELECT format('CREATE ROLE superset_ro LOGIN PASSWORD %L', :'superset_ro_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'superset_ro') \gexec
SELECT format('CREATE ROLE superset_meta LOGIN PASSWORD %L', :'superset_meta_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'superset_meta') \gexec

ALTER ROLE pipeline PASSWORD :'pipeline_password';
ALTER ROLE dbt PASSWORD :'dbt_password';
ALTER ROLE superset_ro PASSWORD :'superset_ro_password';
ALTER ROLE superset_meta PASSWORD :'superset_meta_password';

CREATE SCHEMA IF NOT EXISTS silver AUTHORIZATION pipeline;
CREATE SCHEMA IF NOT EXISTS audit AUTHORIZATION pipeline;
CREATE SCHEMA IF NOT EXISTS intermediate AUTHORIZATION dbt;
CREATE SCHEMA IF NOT EXISTS analytics AUTHORIZATION dbt;

GRANT CONNECT ON DATABASE :"app_database" TO pipeline, dbt, superset_ro;
GRANT USAGE, CREATE ON SCHEMA silver, audit TO pipeline;
GRANT USAGE ON SCHEMA silver, audit TO dbt;
GRANT USAGE, CREATE ON SCHEMA intermediate, analytics TO dbt;
GRANT USAGE ON SCHEMA analytics TO superset_ro;

ALTER DEFAULT PRIVILEGES FOR ROLE pipeline IN SCHEMA silver
  GRANT SELECT ON TABLES TO dbt;
ALTER DEFAULT PRIVILEGES FOR ROLE pipeline IN SCHEMA audit
  GRANT SELECT ON TABLES TO dbt;
ALTER DEFAULT PRIVILEGES FOR ROLE dbt IN SCHEMA analytics
  GRANT SELECT ON TABLES TO superset_ro;

SELECT format('CREATE DATABASE superset_meta OWNER superset_meta')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'superset_meta') \gexec
SQL
