# PardoX en CaféNorte

PardoX es un motor de DataFrames con núcleo en Rust que escribí y publiqué en
[pardox.io](https://www.pardox.io/). Este documento explica por qué existe, cómo lo integré
en el reto, qué midió y qué encontró. La regla del proyecto es simple: **Polars es la
referencia y PardoX es una alternativa verificada, nunca el camino crítico**
([ADR-005](decisions/ADR-005-PARDOX.md), [SPEC-003](specs/SPEC-003-ENGINE-PARITY.md)).

## 1. ¿Por qué existe PardoX?

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

## 2. Cómo lo integré en el reto

- **Alcance:** `sales.csv`, la fuente más grande, recorre PardoX de punta a punta: lectura,
  tipado, validación de contrato, transformación y carga a PostgreSQL. Inventario (JSON anidado,
  que PardoX 0.3.4 no lee), Shopify y tipo de cambio se quedan en Polars por alcance.
- **Separado del pipeline principal:** PardoX escribe en el esquema `silver_pardox`; el pipeline
  oficial siempre lee `silver`. Si PardoX falla, las respuestas no se ven afectadas.
- **Carga nativa:** usa `to_sql`, que escribe a PostgreSQL desde Rust sin pasar por Python.
- **Versión fijada:** `pardox==0.3.4` en `pyproject.toml` y `uv.lock`.
- **Plataformas:** macOS arm64 probado; macOS Intel incluido pero no verificado; Linux x86-64
  en CI; Linux ARM64 sin binario (el pipeline principal sigue funcionando y la validación lo
  reporta como `UNSUPPORTED_PLATFORM`).

## 3. Cómo se comprueba que da el mismo resultado

Antes de medir velocidad hay que demostrar que el resultado es idéntico:

- La paridad se compara **dentro de PostgreSQL**, fila por fila, en las dos direcciones
  (`silver.pos_sales` contra `silver_pardox.pos_sales`), además de conteos, sumas y agregados
  por tienda × mes y por tipo de comprobante.
- **Control negativo:** la prueba altera a propósito un monto y borra una fila en
  `silver_pardox`, y verifica que la paridad detecte exactamente esa diferencia. Así se demuestra
  que la prueba puede fallar.
- La paridad corre en cada `./scripts/validate.sh` en las plataformas soportadas.

## 4. Tiempos

Medianas de seis corridas alternadas, con imports y conexión fuera del cronómetro. Detalle,
llamadas exactas de cada motor y registros completos en
[`benchmark.md`](../artifacts/evidence/benchmark.md).

| Filas | Ruta | Carga a PostgreSQL | Total |
|---|---|---:|---:|
| 86,490 | Polars (ADBC) | 0.319 s | 0.442 s |
| 86,490 | PardoX `to_sql` | 0.113 s | 0.174 s |
| 86,490 | Python `psycopg` | 0.761 s | 1.067 s |
| 864,900 | Polars (ADBC) | 2.033 s | 2.665 s |
| 864,900 | PardoX `to_sql` | 1.385 s | 1.964 s |
| 864,900 | Python `psycopg` | 10.385 s | 13.858 s |

**Cómo leerlo, sin exagerar:**

- PardoX gana el total en los dos volúmenes gracias a la **carga nativa a PostgreSQL**.
- La ventaja se reduce al crecer: de unas 2.5 veces a 86 mil filas a unas 1.36 veces a 865 mil.
- A 865 mil filas, **Polars es mejor en las operaciones en memoria** (validación y agregación).
- En 0.3.4 PardoX no tiene extracción por expresión regular ni conversión de texto a fecha, así
  que su etapa de transformación hace menos trabajo que la de Polars. Pesa milisegundos y no
  cambia la conclusión, pero se declara.
- El archivo `.prdx` escribe más rápido que el parquet de Polars, pero pesa más (2.4 MB contra
  0.9 MB). Su argumento es velocidad de escritura y recarga, no compresión.
- Con estos volúmenes ningún motor se acerca a su límite; mi prueba propia de 640 millones de
  filas está descrita arriba y no forma parte de la evidencia de este reto.

## 5. Lo que encontró la prueba de paridad

A 864,900 filas, la ruta `to_prdx → write_sql_prdx` cargó todas las filas con las sumas
correctas, pero produjo **721 grupos tienda × mes en lugar de 720**. La ruta `to_sql` sí cuadró.

- **Causa:** al unir varios bloques en un mismo grupo de filas del formato `.prdx`, los datos de
  texto se concatenan pero sus desplazamientos (offsets) no se ajustan al acumulado. Las
  columnas de texto se desplazan entre filas; las numéricas no, por eso los totales engañaban.
- **Cuándo aparece:** a partir de 5 veces el volumen, de forma determinista; a 2 veces no.
- **Qué hice:** la guarda de paridad se negó a publicar ese resultado, excluí esa ruta del
  benchmark a gran volumen y dejé una [reproducción mínima](../artifacts/evidence/pardox-0.3.4-prdx-repro/README.md)
  para corregirlo en la siguiente versión del motor.

Es el mejor argumento a favor de la regla de este proyecto: ningún número se publica sin una
prueba que pueda fallar, tampoco cuando el motor es mío.

## 6. Limitaciones conocidas de 0.3.4 en este reto

- Sin lector de JSON anidado (inventario queda en Polars).
- Sin extracción por expresión regular ni conversión de texto a fecha.
- `to_parquet` existe en el núcleo pero no está expuesto en el paquete publicado.
- Sin binario para Linux ARM64.
- La ruta `.prdx` tiene el error descrito en la sección 5.
