# Perfilado reproducible de fuentes

Generado: 2026-10-02T13:22:53-06:00

Los conteos provienen directamente de `datos/`; no se aplicaron transformaciones Silver ni se modificaron las fuentes.

## `sales.csv`

| Métrica | Evidencia |
| --- | --- |
| Filas | 86490 |
| Rango `fecha_hora` | 2024-10-01 07:04:36 — 2026-03-31 21:08:44 |
| `venta_id` duplicados | 0 |
| Cantidad ≤ 0 | 0 |
| Monto ≤ 0 | 0 |
| Monedas | MXN |
| Tiendas distintas | 40 |

### Tipos de comprobante

| Tipo | Filas | Monto | Precio unitario mediano | Cantidad media | Rango de precio unitario | Cantidad ≤ 0 |
| --- | --- | --- | --- | --- | --- | --- |
| E | 3079 | 1,140,985.33 | 186.08 | 1.573 | 15.70 — 826.69 | 0 |
| I | 82518 | 29,503,069.84 | 179.12 | 1.542 | 15.67 — 828.24 | 0 |
| N | 288 | 100,579.56 | 185.96 | 1.413 | 16.57 — 797.14 | 0 |
| P | 451 | 160,501.27 | 182.34 | 1.534 | 15.74 — 824.22 | 0 |
| T | 154 | 42,117.82 | 149.91 | 1.299 | 15.77 — 811.66 | 0 |

Los cinco tipos tienen cantidades estrictamente positivas y rangos de precio unitario superpuestos (mínimos 15.67 a 16.57; máximos 797.14 a 828.24). No existe evidencia de signo o precio que permita tratar un tipo como resta o excluirlo.

## `inventory.json`

| Métrica | Evidencia |
| --- | --- |
| Claves raíz | metadata, tiendas_info, sku_mappings, catalogo, snapshots |
| Filas `tiendas_info` | 40 |
| Filas `sku_mappings` | 65 |
| Productos de catálogo | 70 |
| Filas `snapshots` | 230776 |
| Rango de snapshots | 2025-10-01 — 2026-03-31 |
| Fechas distintas | 182 |
| Días faltantes dentro del rango | 0 |
| Frecuencia observada | Diaria |
| Duplicados `(fecha, tienda_id, sku_erp)` | 0 |
| Valores `N/A` | 4417 |
| Stocks negativos | 0 |
| Tiendas distintas | 40 |
| Registros de costo | 282 |
| Rango de vigencias de costo | 2024-10-01 — 2026-03-30 |
| Productos con múltiples costos | 70 |

El catálogo guarda vigencias en `catalogo.productos[].cost_history[]` con `fecha_vigencia`, `costo_mxn` y `proveedor`.

### Tiendas ERP frente al relato del cliente

| Ciudad ERP | Región ERP | Zona horaria | Tiendas | Mencionada por cliente |
| --- | --- | --- | --- | --- |
| CDMX | centro | America/Mexico_City | 3 | Sí |
| Cancún | sureste | America/Cancun | 3 | No |
| Chihuahua | centro | America/Chihuahua | 3 | No |
| Ciudad Juárez | frontera | America/Ojinaga | 2 | Sí |
| Guadalajara | centro | America/Mexico_City | 3 | Sí |
| Hermosillo | noroeste | America/Hermosillo | 3 | No |
| León | centro | America/Mexico_City | 3 | Sí (Bajío) |
| Mexicali | frontera | America/Tijuana | 2 | Sí |
| Monterrey | centro | America/Monterrey | 3 | Sí |
| Mérida | sureste | America/Merida | 3 | No |
| Nuevo Laredo | frontera | America/Matamoros | 2 | No |
| Puebla | centro | America/Mexico_City | 3 | No |
| Querétaro | centro | America/Mexico_City | 3 | Sí (Bajío) |
| Reynosa | frontera | America/Matamoros | 2 | No |
| Tijuana | frontera | America/Tijuana | 2 | Sí |

Ciudades del ERP no mencionadas en el reto: Cancún, Chihuahua, Hermosillo, Mérida, Nuevo Laredo, Puebla, Reynosa. `Monterrey` y `Chihuahua` están clasificadas como región `centro`, una inconsistencia que debe reportarse al cliente sin sobrescribir el maestro.

## Evidencia de zona horaria de ventas

| Zona horaria ERP | Hora mínima | Hora máxima | Ventas |
| --- | --- | --- | --- |
| America/Cancun | 7 | 21 | 6451 |
| America/Chihuahua | 7 | 21 | 6398 |
| America/Hermosillo | 7 | 21 | 6490 |
| America/Matamoros | 7 | 21 | 8564 |
| America/Merida | 7 | 21 | 6617 |
| America/Mexico_City | 7 | 21 | 32407 |
| America/Monterrey | 7 | 21 | 6626 |
| America/Ojinaga | 7 | 21 | 4326 |
| America/Tijuana | 7 | 21 | 8611 |

Todas las zonas presentan ventas de 07:00 a 21:00. La distribución es evidencia de que `fecha_hora` ya representa hora local de la tienda; no se aplicará una conversión UTC inventada.

## `ecommerce_orders.parquet`

### Schema físico

```text
order_id: String
fecha: String
product_handle: String
cantidad: Int64
amount: Float64
currency: String
customer_name: String
customer_email: String
customer_rfc: String
shipping_city: String
shipping_address: String
```

| Métrica | Evidencia |
| --- | --- |
| Filas | 9947 |
| Rango de fechas | 2025-04-01 03:12:00 — 2026-03-31 22:31:00 |
| Monedas | EUR, MXN, USD |
| Columnas de PII | customer_name, customer_email, customer_rfc, shipping_city, shipping_address |
| Handles distintos | 33 |
| Handles sin mapping explícito | 6 |
| Lista sin mapping explícito | americano-cafe-grano-032, americano-cafe-molido-052, gourmet-cafe-molido-041, molinillo-mercancia-030, selección-cafe-molido-013, termo-mercancia-031 |

## `exchange_rates.csv` y cobertura FX de e-commerce

| Métrica | Evidencia |
| --- | --- |
| Filas | 730 |
| Rango | 2025-04-01 — 2026-03-31 |
| Monedas | EUR, USD |
| Pares fecha/moneda e-commerce USD/EUR | 625 |
| Pares sin tasa | 0 |

| Moneda | Órdenes | Fechas | Órdenes con tasa | Órdenes sin tasa |
| --- | --- | --- | --- | --- |
| EUR | 470 | 261 | 470 | 0 |
| USD | 2535 | 364 | 2535 | 0 |

### Serie EUR con tasa exactamente 22.0 (63 días)

2025-05-20, 2025-05-21, 2025-06-02, 2025-06-03, 2025-06-06, 2025-06-07, 2025-06-08, 2025-06-09, 2025-07-09, 2025-07-10, 2025-07-12, 2025-07-18, 2025-07-19, 2025-07-26, 2025-07-27, 2025-07-28, 2025-08-07, 2025-08-08, 2025-08-12, 2025-08-13, 2025-08-14, 2025-08-15, 2025-08-20, 2025-08-23, 2025-09-02, 2025-09-10, 2025-09-11, 2025-09-13, 2025-09-14, 2025-09-15, 2025-10-03, 2025-10-05, 2025-10-08, 2025-10-09, 2025-10-10, 2025-10-11, 2025-10-18, 2025-10-20, 2025-10-21, 2025-10-22, 2025-10-28, 2025-10-29, 2025-10-30, 2025-10-31, 2025-11-09, 2025-12-04, 2025-12-05, 2025-12-07, 2025-12-09, 2025-12-11, 2025-12-12, 2025-12-13, 2025-12-17, 2026-03-11, 2026-03-12, 2026-03-14, 2026-03-16, 2026-03-24, 2026-03-25, 2026-03-26, 2026-03-27, 2026-03-28, 2026-03-29

Sesenta y tres observaciones EUR son exactamente `22.0`; la repetición del valor redondo se marca como sospechosa de truncamiento. La tasa se conserva y se usará con `fx_quality_flag`, no se descarta.

## Conciliación de producto

El número final de tres dígitos se extrajo de POS (`CN-00013` → `013`), ERP (`ERP-PROV-MX-013-B` → `013`) y Shopify (`…-013` → `013`). Se aplicó mapping explícito solo cuando `sku_erp` no es nulo; después se usa número como respaldo. Para Shopify el respaldo exige igualdad del nombre normalizado sin acentos, mayúsculas ni separadores.

| Fuente | Método | Filas | Unidades | Monto fuente (monedas mixtas, sin FX) |
| --- | --- | --- | --- | --- |
| POS | explicit | 74141 | 114284 | 26,989,097.62 |
| POS | product_number | 6217 | 9547 | 1,434,008.52 |
| POS | product_number_null_erp | 6132 | 9552 | 2,524,147.68 |
| Shopify | explicit | 6959 | 9289 | 2,254,120.66 |
| Shopify | product_number | 1849 | 2494 | 403,053.27 |
| Shopify | product_number_null_erp | 1139 | 1509 | 326,939.13 |

| Relación | Filas | Unidades | Monto fuente (monedas mixtas, sin FX) |
| --- | --- | --- | --- |
| POS → ERP | 86490/86490 (100.00%) | 133383/133383 (100.00%) | 30,947,253.82/30,947,253.82 (100.00%) |
| Shopify → ERP | 9947/9947 (100.00%) | 13292/13292 (100.00%) | 2,984,113.06/2,984,113.06 (100.00%) |

### Coincidencia de número con nombre distinto

Ningún caso.

### Mappings con `sku_erp` nulo

Un mapping con clave presente pero `sku_erp = null` se trata como ausencia de mapping explícito. Esos casos solo se concilian si el número de producto recuperado existe en `catalogo.productos[].sku_erp`.

| SKU POS | Handle Shopify | Número recuperado | SKU ERP en catálogo |
| --- | --- | --- | --- |
| CN-00006 | estándar-cafe-grano-006 | 006 | ERP-PROV-MX-006-C |
| CN-00016 |  | 016 | ERP-PROV-MX-016-C |
| CN-00026 | premium-cafe-molido-026 | 026 | ERP-PROV-MX-026-A |
| CN-00036 | gourmet-cafe-grano-036 | 036 | ERP-PROV-MX-036-A |
| CN-00046 | termo-mercancia-046 | 046 | ERP-PROV-MX-046-A |

| Fuente | Filas | Unidades | Monto fuente (monedas mixtas, sin FX) |
| --- | --- | --- | --- |
| POS | 6132 | 9552 | 2,524,147.68 |
| Shopify | 1139 | 1509 | 326,939.13 |

Lo no conciliado se enviará a Audit; no se elimina ni se fuerza a un producto.

## Fecha máxima común

**2026-03-31** = mínimo de máximos: ventas 2026-03-31, inventario 2026-03-31, ecommerce 2026-03-31.

## Revisión de instrucciones embebidas (prompt injection)

| Superficie | Revisión | Resultado |
| --- | --- | --- |
| PDF | Texto extraído, metadatos y revisión visual de sus 4 páginas | Sin instrucciones embebidas |
| DOCX | Texto, `w:vanish`, texto blanco, relaciones y `customXML` | Sin instrucciones embebidas |
| ZIP | Inventario de entradas y contenido de los cuatro archivos | Sin instrucciones embebidas |
| Parquet | Schema, cabecera/footer binario y campos de texto de Shopify | Sin instrucciones embebidas |
| JSON | Claves y todos los valores de texto | Sin instrucciones embebidas |

El DOCX contiene `customXML/item1.xml`, pero no instrucciones; tampoco se encontraron runs ocultos (`w:vanish`) ni texto blanco. Los campos de texto de Shopify se revisaron junto con el resto del Parquet.

## Interpretaciones cerradas por el propietario

| Tema | Evidencia | Decisión |
| --- | --- | --- |
| CFDI | Cinco tipos; cantidades y montos positivos; rangos de precios superpuestos. | Todas son ventas. El CFDI se cuenta por tipo; el tipo nunca altera signo ni inclusión. |
| Producto | Número común a POS, ERP y Shopify; cinco mappings tienen `sku_erp` nulo y nombres Shopify validables contra catálogo. | Explícito solo con `sku_erp` válido; respaldo por número+nombre; `match_method`; no conciliado a Audit. |
| IVA | No existe columna de impuesto; categorías con tasas 0% y 16%. | `monto` es importe neto sin IVA como supuesto documentado. |
| Tiendas | ERP contiene ciudades no citadas y regiones inconsistentes. | `tiendas_info` es el maestro: define ciudad, región y zona horaria; las 40 tiendas coinciden en las tres fuentes; las diferencias con el relato del cliente quedan documentadas. |
| FX | Cobertura diaria completa; EUR=22.0 exacto en 63 días. | Tasa de la fecha; se usa y se marca `fx_quality_flag` si es sospechosa. |
| P2 | Snapshots diarios; N/A=4417. | Tienda listada si algún SKU tuvo >3 días con stock=0; N/A rompe; salida conserva detalle. |
| P4 | POS tiene tienda; Shopify no. | POS por tienda; e-commerce como canal `ONLINE`. |
| Ventanas | Máxima fecha común 2026-03-31; inventario 2025-10-01—2026-03-31. | Ancla 2026-03-31; P1 usa esos 6 meses; MoM 2025-04 es `null` sin base. |
| Reconciliación | Tres fuentes difieren en cobertura, identidad y granularidad. | Se prevé un mart Gold que explique diferencias POS/ERP/Shopify. |
