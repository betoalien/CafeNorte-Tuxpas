# ADR 001: Stack local

## Estado

Aceptada.

## Decisión

Usar Python, Pydantic, Polars, PostgreSQL, dbt, Docker, Redis y Apache Superset. Mantener Tableau únicamente como bonus opcional compatible con Gold.

## Consecuencias

La solución separa procesamiento columnar, persistencia, semántica y presentación. Superset local consulta PostgreSQL `analytics` mediante `psycopg2`; sus metadatos viven en una base separada dentro de la misma instancia PostgreSQL. Se acepta el costo operativo porque mejora dbt, concurrencia, RLS y compatibilidad BI.

