# ADR 003 dbt owns semantic modeling

## Estado

Aceptada.

## Decision

dbt es obligatorio y propietario de conciliacion de negocio, dimensiones, hechos, costos temporales, FX, metricas, agregados y marts.

## Limite

No se promete el producto hospedado dbt Semantic Layer. El reto implementa una capa semantica gobernada mediante modelos, YAML, tests, documentacion y objetos Gold.

## Consecuencia

El dashboard no contiene formulas de negocio. Una modificacion de metrica ocurre en dbt y queda versionada y probada.

