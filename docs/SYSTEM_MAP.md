# Mapa conceptual del sistema CafeNorte

## Proposito

Este mapa delimita componentes, responsabilidades y contratos antes de la implementacion.

## Flujo local

```text
datos/ read only
  sales.csv
  inventory.json
  ecommerce_orders.parquet
  exchange_rates.csv
        |
        v
Pydantic control plane
  configuracion
  source contracts
  run manifests
        |
        v
Execution engine
  Polars default
  PardoX controlled alternative
        |
        +--> audit quarantine and quality reports
        |
        v
PostgreSQL silver
        |
        v
dbt staging (silver sources)
        |
        v
dbt intermediate (identity, FX, effective cost)
        |
        v
dbt analytics (dimensions, facts, four answers, reconciliation)
        |
        +--> dimensions and facts
        +--> aggregate tables or materialized views
        +--> business marts
        |
        v
Apache Superset via psycopg2
  analytics read only
  RLS by store
  Redis cache
```

## Limites de responsabilidad

### Pydantic

Valida configuracion, manifests, estructura externa y parametros. No sustituye controles columnares ni tests dbt.

### Polars y PardoX

Leen, tipan, limpian, aplanan y cargan Silver. No definen margen, rotacion ni crecimiento mensual.

### PostgreSQL

Persiste Silver, Audit y Gold. Sirve datos a dbt y consumidores. No contiene logica manual fuera de migraciones y modelos dbt.

### dbt

Concilia identidades, aplica FX y costo temporal, construye dimensiones/hechos, define métricas,
materializa los cuatro marts y reconciliación, exporta respuestas y ejecuta pruebas. Lee solo la
última corrida exitosa indicada por `audit.run_log`.

### Dashboard

En local, Superset usa `psycopg2` y consulta exclusivamente el schema `analytics`; aplica RLS por tienda y no recalcula metricas. Docker Compose incluye Superset, Redis y una base `superset_meta` separada dentro de la misma instancia PostgreSQL. OAuth, Let's Encrypt y el proxy HTTPS pertenecen solo a produccion AWS.

## Mapa AWS

```text
Source extracts -> S3 Bronze -> container or Glue processing -> S3 Silver
       -> Glue Data Catalog -> Athena plus dbt -> S3 Gold
       -> Athena -> PyAthena -> Redis cache -> Superset
```

PostgreSQL es el serving layer local. En AWS, Athena es la primera opcion por costo; Redshift Serverless se evalua cuando concurrencia o latencia lo justifiquen.
