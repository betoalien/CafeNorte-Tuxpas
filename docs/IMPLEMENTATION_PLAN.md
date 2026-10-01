# Plan de implementacion

## Fase 0 Gobierno

- Adoptar metodologia universal.
- Aprobar contratos, metricas y ADRs.
- Confirmar privacidad y distribucion de datos.

**Gate:** Definition of Ready satisfecha.

## Fase 1 Harness y plataforma local

- Crear proyecto Python y versiones fijadas.
- Crear Dockerfile y Compose local con PostgreSQL, Redis y Superset, sin proxy TLS.
- Crear `superset_meta` como base separada en la misma instancia PostgreSQL.
- Conectar Superset al schema `analytics` mediante `psycopg2` con usuario de solo lectura y RLS por tienda.
- Cargar dashboards versionados y crear credenciales iniciales desde secretos externos.
- Implementar healthchecks y scripts operativos.
- Crear roles y schemas.

**Gate:** `start`, `stop`, `restart` y `reset` son idempotentes y seguros.

## Fase 2 Bronze y Silver

- Implementar contratos Pydantic.
- Implementar Polars como referencia.
- Guardar manifests, calidad y cuarentena.
- Cargar Silver en PostgreSQL.

**Gate:** conteos reconciliados y PII ausente de Silver.

## Fase 3 PardoX

- Implementar adapter para capacidades publicadas.
- Generar `.prdx` de demostracion.
- Cargar ruta comparable en PostgreSQL.
- Validar paridad antes de medir rendimiento.

**Gate:** cero diferencias no explicadas en resultados acordados.

## Fase 4 dbt y Gold

- Sources y staging.
- Conciliacion de productos, FX y costos temporales.
- Dimensiones, hechos, agregados y marts.
- Tests, documentacion y lineage.

**Gate:** `dbt build` y reconciliaciones de negocio aprobadas.

## Fase 5 Entrega

- Cuatro respuestas reproducibles.
- Propuesta AWS de maximo dos paginas.
- Superset local sobre PostgreSQL `analytics`, con caché Redis, RLS y dashboards reproducibles.
- Especificacion AWS separada: conector Athena, OAuth, Let's Encrypt y HTTPS/443 solo en produccion.
- README y AI log completos.
- Ensayo de demo y pitch.

**Gate:** ejecucion limpia desde Docker y evidencia guardada.

