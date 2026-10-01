# ADR 002 PostgreSQL as local serving layer

## Estado

Aceptada; reemplaza la alternativa DuckDB en el camino principal.

## Decision

PostgreSQL persiste Silver, Audit, Intermediate y Analytics. Streamlit y Tableau consumen exclusivamente Analytics.

## Alternativa considerada

DuckDB simplifica una demo local, pero agrega menos valor al caso multiusuario y no aprovecha la integracion nativa PostgreSQL de PardoX.

## Consecuencias

Docker Compose debe incluir healthcheck, inicializacion idempotente, roles y volumen. En AWS esta decision no obliga a usar RDS; la primera arquitectura productiva sigue siendo S3, Glue Catalog y Athena.

