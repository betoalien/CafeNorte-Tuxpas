# ADR 003 dbt owns semantic modeling

## Estado

Aceptada.

## Decision

dbt es obligatorio y propietario de conciliacion de negocio, dimensiones, hechos, costos temporales, FX, metricas, agregados y marts.

La conciliación `match_method` se resuelve en dbt (Bloque C), no durante la carga Silver. Silver
solo publica columnas técnicas (`product_number` y, en Shopify, `handle_name_normalized`) para que
la regla pueda probarse y versionarse en el propietario semántico.

## Limite

No se promete el producto hospedado dbt Semantic Layer. El reto implementa una capa semantica gobernada mediante modelos, YAML, tests, documentacion y objetos Gold.

## Consecuencia

El dashboard no contiene formulas de negocio. Una modificacion de metrica ocurre en dbt y queda versionada y probada.
