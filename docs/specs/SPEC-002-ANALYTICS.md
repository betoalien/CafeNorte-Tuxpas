# SPEC 002 Analytics and semantic modeling

## Objetivo

Construir con dbt un modelo analitico que produzca respuestas consistentes y auditables para las cuatro preguntas.

## Incluye

- Sources, staging, intermediate y analytics.
- Identidad canonica de producto.
- FX diario y costo efectivo temporal.
- Dimensiones, hechos, agregados y marts.
- Tests genericos, singulares y reconciliaciones.

## Criterios de aceptacion

```text
Given una venta en USD o EUR con tasa disponible
When se construye fct_sales
Then el importe MXN usa la tasa de la fecha de venta
```

```text
Given multiples costos historicos de un producto
When se calcula margen
Then se usa la ultima vigencia no posterior a la venta
```

```text
Given una secuencia de stock cero interrumpida por N/A
When se detectan quiebres
Then N/A no se cuenta como dia de stock cero
```

```text
Given un SKU sin mapping
When se construye Gold
Then su impacto aparece en una reconciliacion y no desaparece silenciosamente
```

## Evidencia

- `manifest.json` y `run_results.json` de dbt.
- Resultados de las cuatro consultas.
- Reconciliacion por filas, unidades y monto.

