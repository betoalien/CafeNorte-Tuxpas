# Contrato de metricas de negocio

## Principios

- Todas las ventas monetarias se expresan en MXN.
- Las metricas se calculan en dbt y no en el dashboard.
- Cada mart incluye periodo, timestamp de construccion y version logica.
- Los datos no conciliados se cuantifican junto al resultado.

## Rotacion de inventario

```text
inventory_turnover_ratio = units_sold / average_valid_inventory_units
```

- Ventana: 2025-10-01 a 2026-03-31, anclada en la fecha máxima común 2026-03-31;
  los snapshots cubren exactamente esos seis meses.
- Grano: producto canonico.
- `N/A` se excluye del promedio y reduce cobertura.
- Inventario promedio cero produce resultado indefinido, no infinito.
- SKU sin mapping se reporta fuera del ranking certificado.

## Quiebre de stock

Una tienda se lista si al menos uno de sus SKU presenta una secuencia de más de tres días
calendario consecutivos con stock igual a cero.

- Ventana: trimestre calendario 2026-01-01 a 2026-03-31, anclada en 2026-03-31.
- `N/A` rompe la continuidad y no cuenta como cero.
- La salida conserva tienda, SKU, fecha inicial, fecha final y número de días.

## Crecimiento mensual por canal

```text
mom_growth_pct = (current_month_sales_mxn / previous_month_sales_mxn) - 1
```

- La serie certificada agrupa por tipo: `FISICO` suma las 40 tiendas POS y `ECOMMERCE` representa `ONLINE`; también se conserva el detalle por tienda y `ONLINE`.
- El director ve las 4 respuestas de toda la red; cada gerente ve las 4 respuestas solo de su tienda, en su propio dashboard.
- `mart_inventory_turnover_by_store` es una vista operativa para la rotación por tienda; no es una respuesta certificada. Las respuestas certificadas siguen siendo las de red.
- Ventana: últimos doce meses, anclada en 2026-03-31.
- Abril de 2025 produce `null` porque no existe marzo de 2025 como base comparable.
- Una base previa igual a cero produce `null` y una razon explicita.
- FX usa la tasa de la fecha de la venta.
- Una tasa EUR de 22.0 se usa con `fx_quality_flag = 'suspected_truncation'`.

## Margen

```text
gross_margin_mxn = sales_amount_mxn - quantity * effective_unit_cost_mxn
```

- El costo efectivo es la ultima vigencia menor o igual a la fecha de venta.
- Para POS se reporta producto y tienda.
- E-commerce se asigna al canal `ONLINE`, no a una tienda fisica inventada.
- Ventas sin mapping, tasa o costo valido se reportan en Audit.
- `monto` se interpreta como importe neto sin IVA: no existe una columna de impuesto y las
  categorías mezclan tasas de 0% y 16%.
- `tipo_comprobante` es un atributo del CFDI; todas las filas son ventas y el tipo nunca altera
  signo ni inclusión. Los CFDI se cuentan por tipo, no se suman ni se restan.

## Objetos Gold

- `analytics.dim_channel`
- `analytics.dim_date`
- `analytics.dim_product`
- `analytics.dim_store`
- `analytics.fct_sales`
- `analytics.fct_inventory_daily`
- `analytics.mart_inventory_turnover_top10`
- `analytics.mart_inventory_turnover_by_store` (vista operativa por tienda; no es una respuesta certificada)
- `analytics.mart_stockouts_over_3_days`
- `analytics.mart_monthly_channel_growth`
- `analytics.mart_monthly_channel_type_growth`
- `analytics.mart_negative_margin_products`
- `analytics.mart_source_reconciliation`

Todos son tablas reconstruidas por `dbt build`; a este volumen la reconstrucción tarda segundos.
`mart_source_reconciliation` explica por periodo, producto y canal por qué difieren POS, ERP y
Shopify: cobertura temporal, mappings, FX, granularidad y registros enviados a Audit.

## Decisiones de interpretación

La [evidencia de perfilado](../artifacts/evidence/profiling.md#interpretaciones-cerradas-por-el-propietario)
fija además estas reglas de semántica:

1. `tipo_comprobante` solo segmenta conteos de CFDI; todas las filas son ventas y ningún tipo
   cambia el signo de monto o cantidad.
2. Silver solo expone las columnas técnicas; dbt resuelve la identidad de producto. La regla usa
   mapping explícito solo si `sku_erp` no es nulo y luego número con nombre validado; `match_method`
   admite `explicit`, `product_number` y `product_number_null_erp`, y separa lo no conciliado en Audit.
3. `monto` es neto sin IVA como supuesto documentado.
4. `dim_store` toma ciudad, región y zona horaria exclusivamente de `tiendas_info` del ERP; las
   ciudades/regiones inesperadas se publican como discrepancia de calidad.
5. FX usa la tasa del día y conserva EUR=22.0 con `fx_quality_flag`.
6. P2 usa el trimestre calendario 2026-01-01—2026-03-31; lista la tienda por cualquier SKU con
   secuencia >3 días en cero, recorta rachas iniciadas antes de la ventana y marca
   `starts_before_window`; `N/A` y días faltantes rompen la secuencia.
7. P4 usa tienda para POS y canal `ONLINE` para e-commerce; su ventana es 2025-04-01—2026-03-31 (12 meses, alineada con P3).
8. Toda ventana se ancla en 2026-03-31; P1 cubre 2025-10-01—2026-03-31, P4 cubre 2025-04-01—2026-03-31 y MoM 2025-04 es `null`.
9. `analytics.mart_source_reconciliation` explicará las diferencias entre las tres fuentes.
