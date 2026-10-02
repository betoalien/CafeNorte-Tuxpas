# CaféNorte: plataforma de datos reproducible

[![CI](https://github.com/betoalien/CafeNorte-Tuxpas/actions/workflows/ci.yml/badge.svg)](https://github.com/betoalien/CafeNorte-Tuxpas/actions/workflows/ci.yml)

«Tenemos datos en tres lugares distintos y cada área reporta un número diferente.» Así describió CaféNorte su problema: una cadena de ~40 cafeterías y una tienda Shopify que vende a México, EE. UU. y Europa, con un POS, un ERP legacy y Shopify que no se ponen de acuerdo, y un presupuesto de USD 200 al mes en AWS. Construí una plataforma que los concilia en un solo número confiable, responde las cuatro preguntas del negocio y se levanta con un comando. Lo más importante no fue el stack: fue encontrar dónde los datos no cuadraban y hacerlo visible en vez de esconderlo.

## El reto

El PDF pide ingerir, normalizar y conciliar las fuentes, persistir un modelo analítico,
responder cuatro preguntas y entregar una propuesta AWS con tests mínimos. Las fuentes
son `sales.csv` del POS (CSV, 86,490 filas), `inventory.json` del ERP legacy (JSON
anidado, 230,776 snapshots) y `ecommerce_orders.parquet` de Shopify (9,947 órdenes).
Esta solución también conserva `exchange_rates.csv` para convertir moneda con trazabilidad.

Las preguntas son: top 10 SKUs por rotación en los últimos seis meses; tiendas con
quiebres de stock de más de tres días en el último trimestre; crecimiento mes a mes de
ventas por canal físico y e-commerce en el último año; y productos con margen negativo
y las tiendas donde ocurre. El límite de infraestructura indicado es aproximadamente
USD 200 mensuales.

## Lo que encontré

Cinco mappings tienen `sku_erp` nulo: 6,132 ventas, por 2,524,147.68 MXN, habrían
parecido conciliadas si se hubiera contado solo la existencia de la clave. Los tipos
CFDI son I=82,518, E=3,079, P=451, N=288 y T=154; se cuentan sin cambiar signo ni
inclusión. `N/A` representa 4,417 snapshots desconocidos, no stock cero. EUR=22.0
aparece durante 63 días: se usa con `suspected_truncation`. El ERP trae 15 ciudades;
el relato menciona CDMX, Bajío, Monterrey, Guadalajara y la frontera, por lo que las
siete ciudades no mencionadas y las regiones inconsistentes se reportan sin corregirlas.
La PII de Shopify se excluye de Silver y Gold. La hora POS se interpreta como hora
local de la tienda. Las interpretaciones largas viven en [`profiling.md`](artifacts/evidence/profiling.md)
y [`docs/BUSINESS_METRICS.md`](docs/BUSINESS_METRICS.md).

## Las respuestas

| Pregunta del PDF | Respuesta | Periodo |
|---|---|---|
| Top 10 SKUs por rotación | `057-C` 1.362, `012-B` 1.226, `041-D` 1.201 | 2025-10-01—2026-03-31 |
| Tiendas con quiebres >3 días | `T015`, `T023`, `T038` | 2026-01-01—2026-03-31 |
| Crecimiento MoM por canal | `FISICO` suma las 40 tiendas; `ECOMMERCE` es ONLINE; se conserva el detalle | 2025-04-01—2026-03-31 |
| Productos con margen negativo | `015-D` −158,216.09, `002-B` −47,595.85, `001-A` −12,663.62 MXN | 2025-04-01—2026-03-31 |

Interpreté las ventanas con ancla común 2026-03-31. La rotación usa unidades POS e
inventario ERP válido de la red; el trimestre es calendario; P3 publica físico/e-commerce
y drill-down por tienda; P4 usa el costo vigente en la fecha de venta. Las respuestas
completas y sus consultas están en [`artifacts/evidence/answers/`](artifacts/evidence/answers/).
En términos de negocio, `015-D` combina volumen con margen negativo porque su costo
supera el precio de venta: revisaría precio y proveedor antes de crecer ese SKU.

## Cómo lo construí

```text
datos/ (solo lectura) -> contratos + cuarentena -> Polars -> PostgreSQL Silver
                                             -> dbt -> analytics Gold -> Superset/RLS
                                             -> audit, manifests y evidencia
                                      PardoX: ruta alternativa aislada para sales.csv
```

Conservé las fuentes inmutables y registré hashes porque una cifra sin procedencia no
resuelve el problema del cliente. Pydantic valida por registro y cuarentena lo inválido.
Polars es la referencia proporcional al volumen; PostgreSQL reemplaza DuckDB porque
necesito transacciones, roles y serving; dbt es dueño de conciliación, FX, costos y
métricas; Superset solo consulta Gold con RLS. Los detalles y ADRs están en
[`docs/TECH_STACK.md`](docs/TECH_STACK.md), [`docs/decisions/`](docs/decisions/) y
[`docs/SYSTEM_MAP.md`](docs/SYSTEM_MAP.md).

## Cómo sé que es correcto

Recálculé resultados desde los archivos originales y comparé hashes con
[`datos/SHA256SUMS`](datos/SHA256SUMS). dbt prueba invariantes y cifras, pytest prueba
contratos, cuarentena, idempotencia y transformación, y el control negativo de paridad
detecta alteraciones reales. También probé RLS con la API y ejecuté el flujo desde un
clon limpio. La revisión encontró tres errores importantes antes de cerrar: P1 mezclaba
granos y quedaba inflada unas 40 veces, P4 no filtraba su ventana y RLS estaba declarado
en YAML pero no aplicado; están explicados en [`AI_LOG.md`](AI_LOG.md).

## Alcance y prioridades

El reto estimaba 2 a 4 horas de trabajo efectivo. Cerré primero el núcleo pedido:
fuentes conciliadas, modelo analítico, cuatro respuestas, propuesta AWS y AI_LOG,
verificado dentro de ese tiempo efectivo (commit [`db9c980`](https://github.com/betoalien/CafeNorte-Tuxpas/commit/db9c980)). Después agregué endurecimiento operativo en bloques pequeños, cada uno con validación y commit propios.

| Lo que agregué | Riesgo que atiende |
|---|---|
| Superset con RLS | Un solo lugar de consulta sin mezclar tiendas |
| Hashes, cuarentena y reconciliación | Auditar por qué cada área obtiene un número distinto |
| `skipped`/`incremental`/`full` | Cargas diarias de bajo costo |
| CI, doctor, clon limpio y portabilidad | Operación por el equipo de TI |
| PardoX con paridad | Alternativa de motor fuera del camino crítico |

Dejé fuera a propósito el despliegue real en AWS, Airflow/MWAA, alta disponibilidad de
Superset y OAuth/HTTPS; están en la propuesta por fases, no en el demo local. Si hubiera
que entregar solo lo pedido, entregaría exactamente el núcleo; lo demás es endurecimiento
identificado como tal.

## Pruébalo

Requisitos y problemas comunes están en [`docs/INSTALACION.md`](docs/INSTALACION.md).

```bash
git clone <repositorio>
cd CafeNorte-Tuxpas
./scripts/start.sh
./scripts/validate.sh
```

Al terminar aparece `Superset listo` y un reporte HTML. `director` ve la red completa;
`gerente_t001` ve T001 en P2/P3/P4. Las contraseñas se muestran con
`./scripts/credentials.sh`; Windows tiene `scripts\\windows\\start.bat`.

Cuando llegan datos nuevos, `skipped` no toca Silver; `incremental` inserta claves nuevas
y conserva el `run_id` original; `full` reemplaza solo la fuente que cambió estructuralmente.

## PardoX

PardoX carga sales a PostgreSQL más rápido que Polars a ×1 y ×10; Polars gana en cómputo
en memoria a ×10. La guarda de paridad encontró un bug real en `.prdx` 0.3.4, por offsets
UTF-8 sin rebase entre bloques; la [reproducción](artifacts/evidence/pardox-0.3.4-prdx-repro/README.md)
lo deja aislado. Inventario, Shopify y FX permanecen en Polars por el alcance de SPEC-003.

### ¿Por qué existe PardoX?

PardoX nació de una brecha concreta: **pandas se queda sin memoria** con volúmenes grandes y
**Polars**, aunque robusto, vive dentro del ecosistema de dependencias de Python. Spark resuelve
la escala, pero solo habla Java/Scala y Python, y exige una JVM o un clúster.

- **Cero dependencias de lenguaje.** Toda la lógica vive en un núcleo Rust; Python, Node.js y PHP
  son bindings delgados. Leer CSV/Parquet, validar contratos, transformar y escribir a
  PostgreSQL no requiere psycopg2, SQLAlchemy ni pyarrow.
- **Universalidad.** Miles de tiendas en línea y sitios web corren en PHP (Laravel, Symfony) o
  Node.js y necesitan llevar sus datos a un dataset sin un clúster JVM. El paquete incluye
  binarios para macOS (ARM/Intel), Linux x86-64, Windows, Node (N-API) y WASM.
- **Hasta el mainframe.** En una prueba propia del autor, un programa COBOL llamó al núcleo de
  PardoX por FFI (DLL/.so) y convirtió un archivo `.dat` de mainframe con 50 millones de
  registros a `.prdx` en ~90 segundos, sin capas de traducción intermedias.
- **PostgreSQL sin intermediarios.** El protocolo binario de PostgreSQL está implementado en Rust:
  los datos van de la base a la memoria del motor (y de regreso, con `to_sql`) sin convertirse en
  objetos Python.
- **Motor propio, no un wrapper.** El núcleo no depende de Apache Arrow: usa estructuras propias en
  Rust y paralelismo con Rayon, con una heurística que decide qué porcentaje de CPU dedicar a cada
  lectura y escritura según la carga.
- **Formato `.prdx`.** Bloques comprimidos con Zstd pensados para escribir y recargar rápido
  (no para el menor tamaño: en este reto el parquet de Polars pesa menos).

**Qué demuestra en este reto:** paridad fila por fila con Polars sobre `sales.csv`, verificada en
PostgreSQL, y la carga a PostgreSQL más rápida de las tres rutas medidas. Polars gana en cómputo en
memoria a ×10. Polars sigue siendo el motor de referencia; PardoX es una alternativa verificada,
nunca el camino crítico. La guarda de paridad encontró un bug real en la ruta `.prdx` de la
versión 0.3.4 (offsets UTF-8 sin rebase entre bloques), documentado en la reproducción.

**Fuera de este reto:** en una prueba propia del autor (640 millones de filas en 320 CSV, laptop
Ryzen 5 con 16 GB), PardoX tardó 182 s contra 204 s de Polars, con 1.13 GB de RAM.

## Cómo usé IA

Codex implementó cambios y pruebas; Claude revisó contra los datos originales y detectó
errores de magnitud; yo decidí alcance, interpretaciones y qué aceptar o rechazar. Cada
bloque terminó con validación y commit propio. La bitácora completa está en
[`AI_LOG.md`](AI_LOG.md).

## Llevarlo a producción

Propongo S3, Glue, RDS PostgreSQL, ElastiCache Redis y QuickSight bajo una estimación de
USD 34.49/mes, dentro de USD 200, con fases de endurecimiento y preguntas abiertas en
[`docs/PROPUESTA_AWS.md`](docs/PROPUESTA_AWS.md).

## Limitaciones y siguientes pasos

Superset es local y no tiene alta disponibilidad; PardoX es experimental y `write_sql_prdx`
falla la guarda x10; Windows no tiene ejecución Docker verificada en CI. Antes de firmar
preguntaría retención y volumen futuro, SLA, zonas horarias oficiales, reglas de impuestos,
proveedor de costos y requisitos de identidad/HTTPS.

## Mapa de documentación

| Documento | Para qué sirve |
|---|---|
| `docs/INSTALACION.md` | Requisitos y operación local |
| `docs/TECH_STACK.md` | Stack, metodología y recorrido de un registro |
| `docs/DATA_CONTRACTS.md` | Contratos, Silver y auditoría |
| `docs/BUSINESS_METRICS.md` | Métricas, ventanas e interpretaciones |
| `docs/PROPUESTA_AWS.md` | Carta de arquitectura, costo y fases |
| `docs/RUNBOOK.md` | Procedimientos operativos |
| `docs/specs/`, `docs/decisions/` | Especificaciones y decisiones |
| `AI_LOG.md` | Uso de IA, errores y autocrítica |
