# CaféNorte: un solo número para ventas e inventario

[![CI](https://github.com/betoalien/CafeNorte-Tuxpas/actions/workflows/ci.yml/badge.svg)](https://github.com/betoalien/CafeNorte-Tuxpas/actions/workflows/ci.yml)

> «Tenemos datos en tres lugares distintos y cada área reporta un número diferente.»
> — CaféNorte, en la primera reunión

CaféNorte es una cadena de unas 40 cafeterías en CDMX, el Bajío, Monterrey, Guadalajara y la
frontera norte, con una tienda Shopify que vende a México, Estados Unidos y Europa. Su punto de
venta, su ERP y Shopify no coinciden, y el dueño quiere un solo lugar donde ver ventas y rotación
de inventario. El presupuesto: unos USD 200 al mes en AWS.

Este repositorio es mi respuesta. Una plataforma que concilia las tres fuentes, responde las
cuatro preguntas del negocio y se levanta con un comando. Pero la parte que más importa no es el
stack: es que, antes de calcular nada, revisé dónde los datos no cuadraban, y decidí hacerlo
visible en lugar de esconderlo.

---

## 1. Lo que me entregaron

| Fuente | Sistema | Formato | Lo que traía en realidad |
|---|---|---|---|
| `sales.csv` | Punto de venta de las tiendas | CSV | 86,490 ventas (el reto estimaba ~80 mil) |
| `inventory.json` | ERP legacy | JSON anidado | 230,776 conteos diarios de inventario, catálogo, costos y tiendas |
| `ecommerce_orders.parquet` | Shopify | Parquet | 9,947 órdenes en MXN, USD y EUR, con datos personales de clientes |

Y cuatro preguntas:

1. Top 10 SKUs por rotación de inventario en los últimos 6 meses.
2. Tiendas con quiebres de stock de más de 3 días en el último trimestre.
3. Crecimiento mes a mes de ventas por canal (físico vs e-commerce) en el último año.
4. Productos con margen negativo y en qué tiendas ocurren.

## 2. Lo que encontré antes de calcular nada

Cruzar las tablas y sumar habría dado números, pero no números confiables. El perfilado
([`profiling.md`](artifacts/evidence/profiling.md)) mostró varias trampas:

- **Productos que parecían conciliados y no lo estaban.** Cinco equivalencias entre el SKU del
  POS y el del ERP tenían la clave pero el valor vacío. Contarlas como válidas habría dado una
  cobertura del 100% falsa sobre **6,132 ventas por 2,524,147.68 MXN**. Decidí tratarlas como
  ausencia de equivalencia y conciliar por el número de producto, que es común a los tres
  sistemas, dejando registrado el método usado en cada fila.
- **El tipo de comprobante fiscal no es una operación aritmética.** Hay cinco tipos de CFDI
  (I=82,518, E=3,079, P=451, N=288, T=154). La tentación es restar los de egreso; pero todas las
  cantidades son positivas y los precios se traslapan. Decidí contarlos por tipo sin cambiar el
  signo de ninguna venta.
- **"N/A" no es cero.** 4,417 conteos de inventario dicen `N/A`. Si los trato como cero, invento
  quiebres de stock que no existen. Los guardo como "desconocido" y cortan cualquier racha.
- **Un tipo de cambio sospechoso.** El euro vale exactamente 22.0 durante 63 días: huele a
  truncamiento. Lo uso, porque es el dato del día, pero queda marcado.
- **Tiendas que el cliente no mencionó.** En la reunión se habló de CDMX, el Bajío, Monterrey,
  Guadalajara y la frontera; el ERP registra 40 tiendas en 15 ciudades, siete de ellas no
  mencionadas (Cancún, Chihuahua, Hermosillo, Mérida, Nuevo Laredo, Puebla y Reynosa). Comprobé
  que las 40 tiendas del ERP son exactamente las 40 que venden en el POS y las 40 que reportan
  inventario, así que son tiendas reales. Decidí que **el ERP es el maestro**: él define la
  ciudad, la región y la zona horaria de cada tienda, y el pipeline las toma de ahí, incluso
  cuando su región no coincide con el relato (Monterrey y Chihuahua aparecen en "centro"). La
  diferencia con lo que se dijo en la reunión queda documentada, no se corrige a mano.
- **Datos personales.** Shopify trae nombre, correo, RFC y dirección. Nunca salen de la capa de
  entrada.

Las reglas completas están en [`docs/BUSINESS_METRICS.md`](docs/BUSINESS_METRICS.md).

## 3. Las respuestas

| Pregunta | Respuesta | Periodo |
|---|---|---|
| Top 10 SKUs por rotación | Los tres primeros: `057-C` 1.362, `012-B` 1.226, `041-D` 1.201 | oct 2025 – mar 2026 |
| Quiebres de stock de más de 3 días | `T015`, `T023` y `T038`, con una racha de 4 días cada una | ene – mar 2026 |
| Crecimiento por canal | Físico 20.72 M MXN (+2.7% abr→mar); e-commerce 4.23 M MXN (−8.5%); e-commerce = 16.9% de las ventas | abr 2025 – mar 2026 |
| Margen negativo | `015-D` −158,216.09, `002-B` −47,595.85 y `001-A` −12,663.62 MXN, en las 40 tiendas | abr 2025 – mar 2026 |

**Lo que le diría al dueño:**

- El producto `015-D` está entre los que más se venden y es el que más dinero pierde: su costo
  subió por encima de su precio de venta y nadie lo ajustó. Es la recomendación más inmediata:
  revisar precio o proveedor.
- La tienda en línea pierde terreno en el año (−8.5% de abril a marzo) mientras las tiendas
  físicas crecen. Antes de concluir, preguntaría si hubo cambios de catálogo, precios o tipo de
  cambio en Shopify.

**Cómo resolví las ambigüedades** (el reto pide decidir con criterio, sin preguntar):
todas las ventanas terminan en el último día común a las tres fuentes, el 31 de marzo de 2026.
La rotación es de toda la red y usa ventas de tiendas, porque el inventario del ERP es de tiendas.
"Último trimestre" es el trimestre calendario. El crecimiento por canal se publica como físico
contra e-commerce, con el detalle por tienda disponible. El margen usa el costo vigente en la
fecha de cada venta. Las tablas completas y sus consultas están en
[`artifacts/evidence/answers/`](artifacts/evidence/answers/).

## 4. Cómo lo construí

```text
datos/ (solo lectura) → contratos + cuarentena → Polars → PostgreSQL (Silver)
                                              → dbt → PostgreSQL (Gold) → Superset con RLS
                                              → auditoría: manifiestos, rechazos, reconciliación
```

Cada pieza responde a una decisión concreta:

- **Los archivos originales nunca se tocan.** Guardo su huella SHA-256 y la verifico en cada
  corrida. Si alguien los modifica, la validación falla. Un número sin procedencia no resuelve
  el problema de "cada área tiene su cifra".
- **Contratos y cuarentena con Pydantic.** Cada registro se valida; lo que no cumple va a
  cuarentena con su motivo. Nada se descarta en silencio.
- **Polars para preparar los datos.** Es proporcional al volumen: no hace falta Spark para
  300 mil filas.
- **PostgreSQL y no DuckDB** ([ADR-002](docs/decisions/ADR-002-POSTGRESQL-SERVING.md)): necesitaba
  transacciones, roles de acceso y un servidor que un dashboard pueda consultar.
- **dbt es dueño de las reglas del negocio** ([ADR-003](docs/decisions/ADR-003-DBT-SEMANTICS.md)):
  conciliación de productos, tipo de cambio, costo vigente y métricas viven en un solo lugar,
  versionadas y probadas.
- **Superset con seguridad por tienda** ([ADR-006](docs/decisions/ADR-006-SUPERSET.md)): el
  director ve toda la red; un gerente solo ve su tienda.

El detalle de cada tecnología, sus versiones y el recorrido completo de una venta desde el CSV
hasta el dashboard están en [`docs/TECH_STACK.md`](docs/TECH_STACK.md).

## 5. Cómo sé que los números son correctos

"Corre sin error" no significa "da el número correcto". Por eso:

- **Recalculé las cuatro respuestas por separado**, desde los archivos originales y sin usar el
  código del pipeline, y coinciden (los montos, al centavo).
- **Pruebas que pueden fallar.** dbt valida invariantes y cifras de negocio; pytest valida
  contratos, cuarentena, idempotencia y la carga incremental. Varias pruebas incluyen un
  control negativo: se altera un dato a propósito para comprobar que la prueba lo detecta.
- **El acceso por tienda se prueba con datos reales**, entrando como gerente y como director.
- **Todo corre desde un clon limpio**, sin nada de mi máquina; GitHub Actions lo
  repite en Ubuntu en cada push.

La revisión encontró errores reales antes de la entrega, y todos se corrigieron: la rotación
salía inflada unas 40 veces por mezclar el inventario de una tienda con las ventas de toda la
red; el margen negativo no filtraba su periodo; y la seguridad por tienda estaba declarada en un
archivo pero no aplicada. El detalle está en [`AI_LOG.md`](AI_LOG.md).

## 6. Alcance: lo que pedía el reto y lo que agregué

El reto estimaba de 2 a 4 horas de trabajo efectivo. Cerré primero el alcance pedido: las tres
fuentes conciliadas, el modelo analítico, las cuatro respuestas verificadas, las pruebas, la
propuesta y la bitácora. Quedó listo la primera tarde
([`db9c980`](https://github.com/betoalien/CafeNorte-Tuxpas/commit/db9c980)). Después agregué,
de forma deliberada, endurecimiento para operación real, en bloques pequeños, cada uno con su
validación y su commit, de modo que en todo momento hubo una entrega completa.

Cada agregado responde a algo que dijo el cliente:

| Lo que agregué | Por qué |
|---|---|
| Dashboard en Superset con seguridad por tienda | «Un solo lugar donde ver ventas y rotación», y cada gerente ve solo lo suyo |
| Huellas de los originales, cuarentena y reconciliación | «Cada área reporta un número diferente»: cada cifra se puede rastrear hasta su fuente |
| Carga que detecta si hubo cambios (sin cambios, incremental o completa) | Corridas diarias baratas dentro de USD 200 al mes |
| Validación desde cero, CI y soporte para macOS, Linux y Windows | Que su equipo de TI pueda operarlo sin depender de mí |
| PardoX, mi propio motor, con prueba de paridad | Una alternativa verificada, fuera del camino crítico |

Dejé fuera a propósito el despliegue real en AWS, un orquestador como Airflow
([ADR-004](docs/decisions/ADR-004-NO-AIRFLOW-KAFKA.md)), la alta disponibilidad del dashboard y
el inicio de sesión corporativo: están en la propuesta por fases. Si hubiera que entregar solo lo
pedido, entregaría exactamente el núcleo; lo demás está identificado como endurecimiento.

## 7. Pruébalo

Con Docker, `uv` y Git instalados, son tres comandos:

```bash
git clone https://github.com/betoalien/CafeNorte-Tuxpas.git
cd CafeNorte-Tuxpas
./scripts/start.sh
```

**Antes de correrlo, sigue la guía de tu sistema operativo en
[`docs/CONFIGURACION.md`](docs/CONFIGURACION.md)**: macOS, Windows (nativo o con WSL2),
Ubuntu/Debian y Fedora/RHEL, paso a paso, con la verificación de cada requisito, qué esperar
al arrancar, cómo entrar al dashboard como director o como gerente y cómo resolver los
problemas comunes.

## 8. PardoX

PardoX es un motor de DataFrames que escribí en Rust ([pardox.io](https://www.pardox.io/)). En
este proyecto es una alternativa verificada, no el camino principal: procesa `sales.csv` de punta
a punta y su resultado se compara fila por fila con Polars. Su carga nativa a PostgreSQL fue la
más rápida de las rutas medidas, y la prueba de paridad encontró un error real en mi propio motor.
Por qué lo creé, cómo se integró, los tiempos y ese hallazgo están en
[`docs/PARDOX.md`](docs/PARDOX.md).

## 9. Cómo usé IA

Trabajé con dos asistentes con roles separados: Codex implementaba y Claude revisaba contra los
datos originales. Yo decidía el alcance, las interpretaciones del negocio y qué aceptar o
rechazar. El patrón de error más repetido de la IA fue *declarar en vez de ejecutar*: una prueba
que no podía fallar, una regla escrita pero no aplicada. La bitácora completa, con los prompts
clave, los errores y mi autocrítica, está en [`AI_LOG.md`](AI_LOG.md).

## Llevarlo a producción

Para producción propongo una plataforma batch diaria en `us-east-1`: S3 para guardar los datos
en sus tres capas; Lambda y ECS/Fargate para la ingesta y el procesamiento; Glue Catalog, Athena
y dbt para el catálogo, las consultas y las reglas de negocio; Apache Superset en Lightsail 4 GB
con inicio de sesión corporativo y HTTPS; Secrets Manager para las credenciales; CloudWatch y
CloudTrail para operación y auditoría. Costo estimado: **USD 34.49 al mes**, USD 165.51 por debajo
del límite. Descarté QuickSight porque su costo crece con cada usuario.
Ver [`docs/PROPUESTA_AWS.md`](docs/PROPUESTA_AWS.md) y su versión en
[PDF](artifacts/evidence/PROPUESTA_AWS.pdf).

## Limitaciones y preguntas abiertas

- El dashboard local no tiene alta disponibilidad; en producción es una sola instancia con
  respaldos.
- PardoX es experimental: su ruta `.prdx` tiene el error encontrado y está excluida a gran volumen.
- En Windows nativo el flujo completo está soportado pero no verificado en CI, porque GitHub no
  corre contenedores Linux en Windows.
- Antes de firmar le confirmaría al cliente: ¿el inventario del ERP también surte al
  e-commerce?, ¿el monto de venta es neto de IVA?, ¿el euro a 22.0 es un error de su
  proveedor de tipo de cambio? y ¿por qué cinco equivalencias de producto quedaron vacías en el
  ERP? (Ya se concilian por número de producto; la pregunta es para corregir el origen).

## Mapa de la documentación

| Documento | Para qué sirve |
|---|---|
| [`docs/CONFIGURACION.md`](docs/CONFIGURACION.md) | Instalación y operación paso a paso por sistema operativo |
| [`docs/PARDOX.md`](docs/PARDOX.md) | PardoX: por qué existe, integración, tiempos y hallazgos |
| [`docs/TECH_STACK.md`](docs/TECH_STACK.md) | Tecnologías, metodología y recorrido de una venta |
| [`docs/PROPUESTA_AWS.md`](docs/PROPUESTA_AWS.md) | Propuesta para el cliente: arquitectura, costo y fases |
| [`docs/BUSINESS_METRICS.md`](docs/BUSINESS_METRICS.md) | Definición de cada métrica e interpretación |
| [`docs/DATA_CONTRACTS.md`](docs/DATA_CONTRACTS.md) | Contratos de cada fuente y capa |
| [`docs/RUNBOOK.md`](docs/RUNBOOK.md) | Operación: comandos y recuperación |
| [`docs/decisions/`](docs/decisions/) · [`docs/specs/`](docs/specs/) | Decisiones de arquitectura y especificaciones |
| [`artifacts/evidence/`](artifacts/evidence/) | Evidencia de cada validación |
| [`AI_LOG.md`](AI_LOG.md) | Cómo usé IA, qué rechacé y qué se corrigió |
