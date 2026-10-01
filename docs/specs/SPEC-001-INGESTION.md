# SPEC 001 Ingestion and Silver

## Objetivo

Convertir las fuentes entregadas en entidades Silver tipadas, trazables y libres de PII innecesaria.

## Incluye

- Validacion Pydantic de configuracion y manifests.
- Ingestion con Polars.
- Cuarentena y reportes.
- Carga idempotente a PostgreSQL.

## Excluye

- Metricas de negocio.
- Streaming.
- Airflow y Kafka.

## Criterios de aceptacion

```text
Given los archivos originales montados como solo lectura
When se ejecuta la ingestion
Then los archivos no cambian y se registra su SHA-256
```

```text
Given un stock con valor N/A
When se normaliza inventario
Then stock_quantity es null y el registro conserva valor y motivo
```

```text
Given campos PII de Shopify
When se publica Silver
Then esos campos no existen en el schema analitico
```

```text
Given una segunda ejecucion con las mismas entradas
When se carga Silver
Then no aparecen duplicados y los conteos permanecen estables
```

## Evidencia

- Manifest por fuente.
- Conteos input, accepted y rejected.
- Tests de contrato.
- Consulta de ausencia de PII.

