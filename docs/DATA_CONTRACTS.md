# Contratos de datos

## Reglas comunes

- Todo archivo recibe SHA-256, tamano, timestamp de ingestión y version de contrato.
- Los identificadores se preservan como texto.
- Los timestamps conservan el valor original y una representacion normalizada.
- Un registro invalido se conserva en Audit con fuente, motivo y payload permitido.
- PII no se replica a Silver salvo autorizacion y necesidad explicita.

## POS sales

**Archivo:** `datos/sales.csv`

**Clave:** `venta_id`

| Campo | Tipo Silver | Regla |
|---|---|---|
| venta_id | text | requerido y unico |
| fecha_hora | timestamp | requerido; timezone documentada |
| tienda_id | text | requerido |
| sku | text | requerido |
| cantidad | bigint | mayor que cero |
| monto | numeric | positivo; importe neto sin IVA (supuesto documentado) |
| moneda | text | esperado MXN |
| tipo_comprobante | text | atributo del CFDI emitido; conservar código original |

Todos los registros son ventas. `tipo_comprobante` se usa para contar CFDI por tipo; nunca
modifica el signo de `monto` o `cantidad` ni determina la inclusión del registro. El perfilado
muestra cantidades positivas y rangos de precio unitario superpuestos en los cinco tipos
([evidencia](../artifacts/evidence/profiling.md#tipos-de-comprobante)). Al no existir una columna
de impuesto y coexistir categorías con tasa 0% y 16%, `monto` se tratará como neto sin IVA.

## ERP inventory

**Archivo:** `datos/inventory.json`

Entidades: metadata, tiendas, mappings, catalogo y snapshots.

**Clave snapshot:** `(fecha, tienda_id, sku_erp)`

`cantidad_en_stock` acepta entero no negativo o el literal `N/A`. Silver almacena:

- `stock_quantity` como entero nullable;
- `stock_raw_value` como texto;
- `quality_status`;
- `quality_reason`.

`N/A` nunca se transforma en cero.

`tiendas_info` es el catálogo maestro. Sus ciudades y regiones se conservan aun cuando difieran
del relato del cliente; la discrepancia queda visible en Audit y en la propuesta
([evidencia](../artifacts/evidence/profiling.md#tiendas-erp-frente-al-relato-del-cliente)).

## Shopify orders

**Archivo:** `datos/ecommerce_orders.parquet`

**Clave:** `order_id`

Campos analiticos permitidos:

- order_id
- fecha
- product_handle
- cantidad
- amount
- currency
- shipping_city solo si se demuestra necesidad analitica y se clasifica adecuadamente

Campos restringidos:

- customer_name
- customer_email
- customer_rfc
- shipping_address

Los campos restringidos no llegan a Silver analitico ni Gold.

## Exchange rates

**Archivo:** `datos/exchange_rates.csv`

**Clave:** `(fecha, currency)`

`rate_to_mxn` debe ser positivo. MXN utiliza tasa 1.0 generada de forma explícita. Se usa la tasa
de la fecha de la orden. Una venta extranjera sin tasa no se convierte silenciosamente y queda
en Audit. Las tasas EUR exactamente iguales a 22.0 se usan, pero reciben
`fx_quality_flag = 'suspected_truncation'` ([63 días observados](../artifacts/evidence/profiling.md#serie-eur-con-tasa-exactamente-220-63-días)).

## Integridad entre fuentes

- La conciliación aplica primero el mapping explícito y después el número de producto de tres
  dígitos común a POS, ERP y Shopify. El respaldo Shopify solo es válido si el nombre del handle
  coincide con `catalogo.nombre` después de normalizar acentos, mayúsculas y separadores.
- Cada registro conciliado conserva `match_method` con valor `explicit` o `product_number`.
- Los mappings faltantes o fallidos se reportan en Audit, no se filtran.
- Se mantiene un `canonical_product_id` nullable hasta resolver identidad.
- La cobertura de mapping se publica por fuente y por monto/unidades afectados.
- Las relaciones dbt bloquean Gold cuando una clave requerida carece de dimension certificada, salvo excepcion documentada.

La cobertura combinada por filas, unidades y monto está cuantificada en
[profiling.md](../artifacts/evidence/profiling.md#conciliación-de-producto).

## Contrato de capas PostgreSQL

| Schema | Escritor | Consumidor | Contenido |
|---|---|---|---|
| silver | Polars o PardoX | dbt | datos tecnicamente normalizados |
| audit | pipeline y dbt | operadores | rechazos, calidad, ejecuciones |
| intermediate | dbt | dbt | modelos internos |
| analytics | dbt | BI | dimensiones, hechos, agregados y marts |

## Decisiones transversales cerradas

Con evidencia en [profiling.md](../artifacts/evidence/profiling.md#interpretaciones-cerradas-por-el-propietario):

1. Los cinco tipos de CFDI representan ventas; se cuentan por tipo y no cambian signos.
2. Producto se concilia por mapping explícito y luego número+nombre; se registra `match_method` y
   lo no conciliado va a Audit.
3. `monto` es neto sin IVA como supuesto por ausencia de impuesto y tasas distintas por categoría.
4. `tiendas_info` es el maestro; sus discrepancias se reportan sin corregirlas silenciosamente.
5. FX usa la tasa diaria; EUR=22.0 se conserva con `fx_quality_flag`.
6. P2 requiere un SKU con más de tres días seguidos en cero; `N/A` rompe la secuencia y se
   conservan tienda, SKU, inicio, fin y días.
7. P4 conserva la tienda POS y asigna Shopify al canal `ONLINE`.
8. Las ventanas se anclan en 2026-03-31; inventario cubre seis meses y MoM 2025-04 es `null`.
9. Gold incorporará un mart de reconciliación POS/ERP/Shopify.

