# Bitácora de IA

## Estado

Bitácora iniciada durante la fase de análisis y arquitectura. Se actualizará conforme avance la implementación.

## Herramientas

- OpenAI Codex, familia GPT-5; no se afirma un identificador más específico porque la interfaz no lo mostró.
- Claude Code (Claude Opus 5.5), utilizado como revisor técnico independiente.
- Herramientas locales de inspección de archivos y perfilado de datos.
- Documentación oficial de AWS, dbt y PardoX para validar capacidades y costos.

## Flujo de trabajo

El ciclo es: **Codex implementa**, **Claude Code revisa con dureza** supuestos, costos, consistencia y riesgos, y **el propietario decide** qué aceptar, modificar o rechazar. Codex aplica la decisión y presenta evidencia; Claude puede revisar la nueva versión. Cuando los agentes no comparten todo el contexto, el propietario resuelve la discrepancia y la bitácora registra la corrección. La especificación permanece separada de la implementación.

## Prompts y decisiones clave

### Prompt 1: Analizar antes de implementar

**Prompt:** "Analiza la documentación, la carpeta datos y UNIVERSAL_ARCHITECTURE.md; primero analicemos lo que requiere antes de dar algún paso".

**Respuesta resumida:** Codex identificó entregables, pesos de evaluación, hallazgos de calidad y una arquitectura serverless proporcional al volumen.

**Decisión humana:** Modificar. Se aceptó la proporcionalidad, pero dbt pasó a ser obligatorio por la importancia de la capa semántica.

### Prompt 2: Hacer dbt obligatorio

**Prompt:** "dbt debe dejar de ser opcional y usarse, porque precisamente parte del reto es la capa semántica".

**Respuesta resumida:** Se separaron responsabilidades entre Pydantic, Polars, dbt, DuckDB y Docker, y se propuso una estructura Harness.

**Decisión humana:** Modificar. Se conservaron Pydantic, Polars, dbt y Docker; posteriormente PostgreSQL sustituyó a DuckDB como capa de servicio.

### Prompt 3: Incorporar PardoX

**Prompt:** "PardoX es el motor que yo programé; la idea es hacer una alternativa y decir que yo desarrollé este motor por esta situación".

**Respuesta resumida:** Tras leer la documentación, se propuso un adaptador alternativo, pruebas de paridad con Polars y una demostración reproducible sin depender de funciones futuras.

**Decisión humana:** Aceptar con restricciones. PardoX será diferenciador técnico; Polars permanecerá como referencia para reducir riesgo.

### Prompt 4: Elegir motor de serving

**Prompt:** "Tengo dudas entre DuckDB o PostgreSQL; Polars o PardoX dan el músculo y la base solo sirve al dashboard".

**Respuesta resumida:** Codex recomendó PostgreSQL por concurrencia, integración con dbt y compatibilidad con los consumidores.

**Decisión humana:** Aceptar. PostgreSQL será la persistencia y capa de servicio local; DuckDB queda fuera del camino principal.

### Prompt 5: Definir el alcance del visor

**Prompt:** "Elimina el punto 5; esto no es parte del proyecto" y, posteriormente, "Apache Superset debe formar parte del Docker final para que el cliente ingrese con el usuario y contraseña asignados y vea los dashboards".

**Respuesta resumida:** El visor se retiró inicialmente. Después de la ampliación explícita del propietario, Codex incorporó Superset, costos, seguridad y operación; una iteración mezcló el conector productivo de Athena con el flujo local.

**Decisión humana:** Modificar. Superset sí es entregable. Localmente usa `psycopg2` contra PostgreSQL `analytics`, Redis, credenciales de demostración y RLS. En AWS usa el conector Athena, OAuth, Let's Encrypt y HTTPS. La región no se divide: todo `us-east-1` con Lightsail, o todo `mx-central-1` con EC2 si Jurídico exige residencia.

### Prompt 6: Implementar únicamente el Bloque A

**Prompt:** "Inicia la implementación según AGENTS.md, docs/specs y los ADR. Solo Bloque A; detente al terminar para revisión". El alcance incluyó perfilado previo, harness Bash, PostgreSQL en Docker, proyecto Python con uv, Ruff y evidencia.

**Trabajo realizado:** Codex generó un perfilador reproducible sin transformar Silver, fijó dependencias en `pyproject.toml` y `uv.lock`, implementó Compose con PostgreSQL versionado, inicialización idempotente, roles, schemas y `superset_meta`, y creó los seis scripts operativos. Se probaron arranque limpio, segundo arranque, estado, validación, reinicio, detención y ambos caminos de reset. Los hashes demostraron que `datos/` permaneció inmutable.

**Hallazgos frente a la especificación:** `sales.csv` solo contiene MXN, por lo que el caso de FX
USD/EUR de SPEC-002 no se ejerce en POS; las monedas extranjeras aparecen en e-commerce. En ese
momento Codex infirió erróneamente que `E` debía interpretarse como egreso, aun cuando todos los
tipos tenían cantidades y montos positivos. El Bloque A-1 eliminó esa inferencia y documentó la
decisión del propietario.

**Estado:** Bloque A implementado y detenido para revisión. No se programó ingestión Silver, PardoX, dbt ni Superset.

### Prompt 7: Corregir el Bloque A antes de Silver

**Prompt:** "Bloque A-1 (correcciones antes del Bloque B). No avances a Silver; detente al
terminar para revisión". El propietario pidió puerto local aleatorio y secretos estables, ampliar
el perfilado de FX, CFDI, tiendas, horarios, mappings y prompt injection, y cerrar nueve
interpretaciones de negocio.

**Trabajo realizado:** Codex reforzó el harness para generar `.env` una sola vez con puerto libre
y contraseñas aleatorias, añadió validación Bash/ShellCheck/Ruff y regeneró el perfil desde las
fuentes. Se midió FX sobre e-commerce, la serie EUR=22.0, duplicados de snapshots, horarios por
zona, catálogo de tiendas y conciliación explícita+producto. Las decisiones se propagaron a
contratos, métricas y README sin implementar Silver.

**Decisión humana:** Aceptar las nueve interpretaciones expresadas por el propietario. En
particular, ningún tipo de CFDI altera el signo de la venta; el número de producto es fallback
válido solo bajo las reglas documentadas; EUR=22.0 se usa con bandera de calidad.

**Estado:** Bloque A-1 implementado y detenido para revisión; Bloque B no iniciado.

### Prompt 8: Revalidar en Mac después de migrar desde Windows

**Prompt:** "Mientras Claude termina de revisar las tareas pendientes, vamos a analizar el proyecto
completo, es una tarea para una entrevista tecnica todo parte del PDF, empezamos codeando en windows
pero pasamos a Mac".

**Trabajo realizado:** Codex confirmó que el PDF del reto no está presente en el checkout actual
aunque está listado en `.gitignore`, revisó arquitectura, especificaciones, ADRs, scripts y
evidencia, y ejecutó el harness en macOS. `start.sh` generó `.env` local ignorado por Git, levantó
PostgreSQL en el puerto 23779 y dejó el contenedor `healthy`.

**Corrección aplicada:** En macOS, `validate.sh` sí ejecutó ShellCheck y detectó SC2251 en tres
negaciones de `port_is_free` dentro de `scripts/start.sh`; Windows había omitido ShellCheck por no
tenerlo instalado. Se reescribieron esas ramas con `if ...; then return 1; fi; return 0` para
preservar la lógica y cumplir ShellCheck.

**Resultado:** La segunda ejecución de `./scripts/validate.sh` pasó en macOS: Compose validó,
PostgreSQL expuso `analytics`, `audit`, `intermediate` y `silver`, los roles esperados existieron,
`superset_meta` existió y Ruff terminó con `All checks passed!`.

### Prompt 9: Bloque A-2 solo correcciones

**Prompt:** "Bloque A-2. Solo correcciones; no avances a Silver. Detente al terminar para
revisión". El propietario pidió corregir la conciliación para no contar `sku_erp = null` como
mapping explícito, eliminar Python de `start.sh`, evitar que `validate.sh` regenere
`profiling.md`, actualizar contratos/README/evidencia y hacer un commit único con lo pendiente.

**Trabajo realizado:** Codex separó `match_method` en `explicit`, `product_number` y
`product_number_null_erp`; regeneró `profiling.md`; actualizó contratos, métricas, README,
runbook y evidencia; eliminó la dependencia de Python en la selección de puerto; y conservó el
alcance sin implementar Silver, dbt, PardoX, Gold ni Superset.

**Resultado:** Las cifras de mappings con `sku_erp` nulo coinciden con lo esperado para POS
(6,132 filas / 2,524,147.68 MXN) y Shopify (1,139 filas). `CN-00016` se reportó con
`handle = null` porque así está en `inventory.json`. ShellCheck y Ruff pasaron sin avisos.

## Casos de error de IA o revisión

- **PardoX malinterpretado:** Codex interpretó inicialmente "PardoX" como "Parquet". El propietario aclaró que es su motor DataFrame; se leyó la documentación y se incorporó con pruebas de paridad.
- **Costo incompleto:** Codex generó la estimación de **USD 2.53/mes**; Claude detectó en la revisión cruzada que omitía ingesta, secretos, seguridad, dev/test, contingencia y visor productivo. Codex reconstruyó el modelo por bloques con fuentes y supuestos.
- **Instrucción del visor atribuida incorrectamente:** Claude reintrodujo el visor sin conocer la instrucción previa del propietario de retirarlo y acusó erróneamente a Codex de haberla ignorado. El propietario detectó la inconsistencia. La lección es que una revisión entre agentes sin contexto compartido puede producir conclusiones falsas; las atribuciones deben comprobarse contra la conversación completa.
- **Arquitectura partida:** Claude recomendó `mx-central-1`, pero Lightsail no existe allí; combinar datos en México con Superset en Virginia creó transferencia entre regiones. Se corrigió a dos opciones coherentes y excluyentes: todo `us-east-1` con Lightsail o todo `mx-central-1` con EC2.
- **CFDI interpretado como operación aritmética:** Claude interpretó `tipo_comprobante` según
  categorías del SAT y propuso restar `E` y excluir `P`, `T` y `N`, lo que habría omitido o
  invertido aproximadamente MXN 1.4 millones de ventas reales. El propietario corrigió que un
  CFDI se cuenta, no se suma. El perfilado confirmó cantidades positivas y rangos de precio
  unitario superpuestos en los cinco tipos.
- **Regla sin evidencia:** Codex propuso previamente "`E` resta; los demás suman" sin evidencia
  en los datos. La regla fue eliminada del perfil y sustituida por la decisión del propietario.
- **Cobertura inflada por clave nula:** Codex reportó 100% de cobertura contando como `explicit`
  mappings que tenían la clave `sku_erp`, pero cuyo valor era `null`. Claude lo detectó al
  contrastar contra `inventory.json`. Lección: que una clave exista no significa que su valor sea
  válido; `sku_erp = null` es ausencia de mapping explícito.

## Hallazgos de revisión aceptados

- Claude detectó que la identidad de producto es recuperable mediante el número común de tres
  dígitos en POS, ERP y Shopify. Codex lo midió con prioridad para mapping explícito y validación
  del nombre normalizado en Shopify.

## Supuestos humanos corregidos por la IA

- **Tamaño y precio de Superset:** el propietario estimó inicialmente USD 20. Claude señaló el requisito de 4 GB de RAM; Codex verificó la tarifa oficial de Lightsail de USD 24/mes, más snapshots.

## Decisiones rechazadas o pospuestas

- Kafka fue rechazado porque las fuentes se procesan por lotes y no existe un requisito de transmisión continua.
- MWAA/Airflow fue pospuesto porque tres flujos batch no justifican su complejidad operacional.
- Se rechazó reabrir DuckDB o rediseñar la arquitectura tecnológica: PostgreSQL y las responsabilidades de cada motor ya estaban resueltos en los ADR.
- Se rechazaron las preguntas al reclutador propuestas por Claude sobre: (a) publicar PII en un repositorio público, (b) si los USD 200 incluían BI y (c) la frecuencia de actualización. No eran necesarias porque los datos son sintéticos, BI es un bonus decidido por el propietario y el procesamiento batch diario es un supuesto razonable para el volumen y el reto.
- Superset es el visor principal. Tableau queda únicamente como bonus opcional, no como entregable requerido.
- Las funciones de PardoX anunciadas para una versión futura no serán dependencia del reto.

## Autocrítica provisional

Las decisiones de alcance, dbt obligatorio, PardoX, PostgreSQL, Superset y región pertenecen al propietario. Codex implementa y documenta; Claude cuestiona; ninguno sustituye la decisión humana. La validez final exige reconciliaciones, pruebas dbt, paridad entre motores, aislamiento RLS, costos reproducibles y evidencia de ejecución.

### Prompt 10: Bloque B Bronze → Silver

**Prompt:** "Implementar Bronze → Silver sin avanzar a dbt, Gold, PardoX ni Superset, con contratos
Pydantic, cuarentena, manifiestos, hashes, carga Polars idempotente, controles de PII y evidencia
macOS".

**Decisiones:** la entrada única es `uv run python -m cafenorte.ingest`; cada corrida genera un
UUID y timestamp, calcula SHA-256 antes/después y reemplaza las tablas Silver dentro de una
transacción. Los snapshots duplicados futuros conservarán la primera fila y enviarán las siguientes
a Audit. `N/A` es desconocido y se carga como `stock_quantity = null`. Silver no calcula
`match_method`: por decisión del propietario y coherencia con ADR-003, dbt lo resolverá en el
Bloque C; Silver solo expone `product_number` y `handle_name_normalized`.

**Errores reales corregidos:** el primer validador aplicó `ge=0` al literal `N/A`; se reemplazó
por una validación explícita que acepta `N/A` o enteros no negativos. Después, el pipeline intentó
crear schemas con `pipeline` y falló por permisos; se eliminó esa creación redundante porque el
init de PostgreSQL es su propietario. La comparación de sumas en pytest se ajustó a `Decimal`,
sin alterar datos ni cifras esperadas.

### Prompt 12: Bloque C dbt → Gold

**Decisiones:** dbt es el único dueño de conciliación, FX, costo temporal y métricas. Staging filtra
la última corrida exitosa de `audit.run_log`; intermediate calcula identidad, tasa y costo; marts
materializa dimensiones, hechos, las cuatro respuestas y reconciliación. P1 usa solo POS para
unidades vendidas; P2 usa el trimestre calendario 2026-01-01—2026-03-31; e-commerce es `ONLINE`.

**Errores reales corregidos:** el primer build pasó técnicamente pero produjo P1 vacío porque la
extracción de `product_number` no contemplaba el sufijo `-A/-B` de los SKU ERP. El profiling ya
demostraba el patrón, así que se corrigió la extracción en Silver y se verificaron las seis cifras
de identidad contra profiling. También falló un test CFDI por referir `cantidad` en staging cuando
la columna se llama `quantity`; se corrigió el test y el build terminó sin skips ni errores.

### Prompt 11: Bloque B-1, correcciones de evidencia y controles

**Decisión:** los hashes se calculan antes de leer cada fuente y después de `load()`; una diferencia
actualiza `audit.run_log` a `failed`. `audit.quarantine` conserva historial por `run_id`; no se
borra entre corridas. La prueba de idempotencia compara conteos, sumas y cuarentena para todas las
tablas Silver, y la prueba de hashes compara el manifest contra SHA-256 calculado desde `datos/`.

**Caso de error:** las pruebas originales de inmutabilidad e idempotencia pasaban sin comprobar
lo que afirmaban: el manifest calculaba `before` y `after` en el mismo punto, y la idempotencia no
comparaba realmente la segunda corrida. Lección: una prueba que no puede fallar no es una prueba.

### Prompt 13: Bloque C-1, corrección de grano en P1

**Caso de error:** P1 mezclaba granos: `units_sold` estaba a nivel de red, mientras el inventario
promediaba registros de una tienda, y aun así pasó 58 tests dbt. Claude lo detectó recalculando desde
las fuentes. **Lección:** un número plausible no es un número correcto; los tests deben validar
magnitud, no solo estructura.

**Corrección:** el inventario promedio de red ahora suma el promedio válido de cada combinación
producto-tienda; la cobertura conserva la proporción de snapshots no `N/A`.

### Prompt 14: Bloque D1, Superset local con Redis y RLS

**Decisiones:** Superset consume exclusivamente `analytics` mediante `superset_ro`; `superset_meta`
guarda metadatos y Redis cachea resultados. Los dashboards, roles y reglas RLS se versionan en
`superset/` y el bootstrap es idempotente. P1 es un indicador de red sin filtro de tienda; el rol
`gerente_t001` se restringe a T001 en P2/P3/P4.

**Verificación:** se fijaron imágenes multi-arquitectura con soporte `linux/arm64`; las credenciales
y puertos se generan fuera del repositorio. La prueba de validación usa el login de la API de
Superset y confirma la presencia del dashboard para los roles demo.

### Prompt 15: Bloque D1-1, corrección de dashboard y RLS

**Caso de error:** D1 reportó PASS con un dashboard vacío y un supuesto test de RLS que solo leía
texto del YAML; además, la cláusula declarada no servía para P3 porque P3 usa `channel`, no
`tienda_id`. **Lección:** validar el comportamiento, no la declaración.

**Corrección:** el bootstrap ahora registra `CafeNorte analytics`, crea cinco datasets, cinco
gráficas y filtros `RowLevelSecurityFilter` reales. La prueba consulta `/api/v1/chart/data` como
gerente y director, comprueba T001/ONLINE y conserva un control negativo sin filtro.

### Prompt 16: Bloque D1-2, modos de carga

**Decisión del propietario:** conservar la transacción y el reemplazo full existentes, añadir la
decisión temprana por SHA-256/clave/`row_hash`, y evitar modelos incrementales dbt porque este
volumen reconstruye Gold en segundos. `skipped` no toca Silver ni ejecuta dbt/exportación;
`incremental` admite solo claves nuevas y cambios o bajas fuerzan `full`.

### Prompt 17: Bloque D1-3, carga incremental real

**Caso de error:** D1-2 registraba `incremental`, pero `load()` seguía recargando todas las
tablas y no había pruebas de los modos. **Lección:** la etiqueta no es el comportamiento; hay que
probarlo con el `run_id` de las filas.

**Corrección:** `load()` ahora aplica el modo por tabla dentro de una sola transacción: `skipped`
no inserta, `incremental` inserta solo claves nuevas y `full` reemplaza únicamente la tabla de la
fuente cambiada. La prueba temporal cubre tres altas, modificación y baja, y restaura el estado con
`--force`. `start.sh` y `validate.sh` calculan el `anchor_date` común desde Silver y lo pasan a dbt.

### Prompt 18: Bloque D2, paridad PardoX

**Decisión:** fijar PardoX `0.3.4` y usar únicamente la API publicada. `read_csv` se ejecuta para
`sales.csv`; JSON anidado, Parquet y la conversión documentada a registros Silver no están
disponibles en la API consultada, así que se registra `engine_fallback=polars` explícitamente.
Polars sigue siendo el oráculo y la carga incremental no se modifica.

**Limitación:** la ruta PardoX no se promociona a Silver ni se simula como equivalente mientras la
API no documente esas operaciones. El benchmark reporta el tamaño pequeño del dataset y no
generaliza sus tiempos.

### Prompt 19: Bloque D2-1, rehacer PardoX

**Caso de error:** D2 comparaba PardoX leyendo CSV contra un `polars_engine.prepare()` vacío,
marcaba cuatro fuentes como fallback y afirmaba limitaciones que sí existen en PardoX `0.3.4`.
**Lección:** un benchmark debe ejecutar el mismo trabajo y las limitaciones deben verificarse en
los docstrings de la versión instalada, no inferirse.

**Corrección:** ambos motores leen, validan, transforman y materializan las fuentes tabulares;
PardoX usa `read_csv`, `read_parquet`, `cast`, `validate_contract`, `to_dict` y `to_prdx`. Solo
`inventory.json` usa fallback Polars porque el lector JSON anidado no existe en la API instalada.
El benchmark corre cada motor en subprocess, mide etapas y memoria, alterna una corrida fría y
cinco calientes, y falla si una etapa con filas reporta menos de 1 ms.

### Prompt 20: Bloque D2-2, PardoX punta a punta en sales

**Caso de error:** D2-1 descartaba la salida de `prepare()` y cargaba `silver_pardox` con datos de
Polars; además, el control negativo solo comparaba desigualdad y el benchmark mezclaba el JSON de
31 MB con Polars, omitía el INSERT real y reportaba KB como MB.

**Corrección:** `build_pos_sales_polars()` y `build_pos_sales_pardox()` comparten contrato de salida
de tuplas Silver con `row_hash`; PardoX usa esa salida exclusivamente para `silver_pardox.pos_sales`.
`check_parity()` se ejecuta antes y después de alterar/restaurar una fila. El benchmark queda limitado
a `sales.csv`, usa PostgreSQL temporal, subprocess, memoria macOS en MB y compara `.prdx` contra
Parquet/CSV serializado con guardas de 86,490 filas.

### Prompt 21: Bloque D2-3, benchmark justo y carga nativa

**Caso de error:** D2-2 llamaba `prepare()` y después el builder, leyendo y convirtiendo `sales.csv`
dos veces; cerca del 90% del tiempo era Python común, Pydantic y `executemany`, y no se usaba el
driver nativo de PostgreSQL de PardoX. La primera implementación de D2-3 también intentó crear la
tabla ADBC en `public`, donde `pipeline` no tiene CREATE, y el stage inicial llegó a devolver 1,024
filas porque `px.DataFrame(list[dict])` trunca ese constructor.

**Corrección:** una sola lectura por subprocess, etapas separadas y carga nativa: PardoX usa
`px.read_csv`, `px.execute_sql`, `df.to_sql` y `df.to_prdx`; Polars usa ADBC
`DataFrame.write_database(..., engine="adbc")`; la línea base usa `psycopg.executemany`. Se verifican
86,490 filas y agregados idénticos. La carga PardoX reveló una diferencia real de `product_number`
para SKUs como `CN-00051`; se corrigió usando los últimos tres dígitos tras limpiar caracteres no
numéricos y la paridad SQL quedó vacía.

**Lección:** un benchmark debe medir el mismo trabajo y la llamada nativa real; permisos, cardinalidad
de salida y transformaciones también son parte de la medición.

### Prompt 22: Corrección posterior, carga PRDX nativa

**Hallazgo:** la revisión de la documentación oficial de PardoX 0.3.4 mostró que faltaba medir
`write_sql_prdx`, la ruta de streaming de un archivo `.prdx` a PostgreSQL. También confirmó que
`to_sql` activa COPY automáticamente sobre 10,000 filas y que las escrituras requieren una tabla
preexistente.

**Corrección:** el benchmark conserva la comparación `df.to_sql` vs ADBC vs `psycopg.executemany` y
añade `df.to_prdx` seguido de `px.write_sql_prdx` en una tabla aislada, verificando 86,490 filas.
La documentación de `date_extract` exige una columna Date/Timestamp/Int64; `fecha_hora` de la fuente
es Utf8 y el intento real devuelve `date_format ... expected Date/Timestamp/Int64`, por lo que no se
simula una transformación PardoX inexistente: la fecha/mes debe normalizarse en la etapa contractual
SQL compartida y queda documentada como limitación de esta versión.

### Prompt 23: Bloque D2-4, benchmark corregido

**Caso de error:** D2-3 cronometro la importación del binario PardoX dentro de `read`, sumó dos
variantes de carga en un mismo total, compartió cronómetros entre transformación y agregación, no
calculó `product_number` ni mes y no validó moneda ni rechazos. La escala x10 también empezó leyendo
el directorio original porque el módulo había capturado `DATA` antes de aplicar `CAFENORTE_DATA_DIR`.

**Corrección:** imports y conexión quedan fuera del total, con una etapa informativa `import`; cada
etapa tiene su propio cronómetro; las variantes `pardox (to_sql)` y `pardox (write_sql_prdx)` tienen
totales separados; se genera una copia temporal x10 con venta_id único y se exige paridad de grupos,
unidades y monto redondeado a dos decimales.

**Resultado real:** la escala base pasa. En x10 los totales globales de `write_sql_prdx` coinciden,
pero su distribución tienda x mes produce 721 grupos frente a 720 y la guarda falla deliberadamente.
No se relaja la prueba: queda como incompatibilidad reproducible de la ruta `write_sql_prdx` a esa
escala en PardoX 0.3.4.

### Prompt 24: Core local de PardoX y Parquet

**Hallazgo:** el core local contiene `pardox_export_to_parquet` y `pardox_write_parquet`, pero el
wheel instalado `pardox==0.3.4` no exporta el símbolo Python. La llamada documentada
`frame.to_parquet(path)` falla en ejecución con `NotImplementedError: pardox_to_parquet not found in Core.`

**Decisión:** no se simula Parquet PardoX con Polars ni se cambia el benchmark para atribuirlo al
motor. Se conserva `.prdx` para la ruta instalada y se registra esta diferencia entre el código fuente
del core y el binario distribuido. Para medir Parquet nativo habrá que reconstruir/reinstalar el binding
con el símbolo exportado y repetir la evidencia.
