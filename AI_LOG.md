# Bitácora de IA

## Herramientas y flujo requerido por el reto

Usé OpenAI Codex en su versión de escritorio con GPT 5.6 Luna Light como implementador,
y Claude Code con Claude Opus 5.5 como revisor independiente. También usé Python 3.12,
uv, Polars, Pydantic, PostgreSQL, dbt, Docker/Compose, Superset, ShellCheck, Ruff,
pytest y la documentación oficial de PardoX y AWS.

Separé los roles a propósito: Codex implementó, Claude revisó contra los archivos originales
y yo decidí qué se aceptaba. Diseñé ese arnés de trabajo (harness engineering) para que cada
agente tuviera un contexto acotado: así aproveché mejor los tokens y repartir las tareas entre
Codex y Claude me dio más margen que exprimir un solo agente. Trabajé en bloques pequeños con la
instrucción “detente al terminar”, cada uno con validación y commit. No usé subagentes ni el modo
plan de las herramientas; el análisis lo hice primero, en un prompt sin código (prompt 1).
Claude Code trabajó sobre el repositorio en mi Mac mediante el puente de dispositivos de la app
de Claude (herramientas MCP remote-devices); Codex trabajó directamente en el repositorio local.

## Prompts clave y decisiones

### 1. Alcance y arquitectura

**Prompt:** “Analiza la documentación, la carpeta datos y UNIVERSAL_ARCHITECTURE.md; primero analicemos lo que requiere”.

**Respuesta:** propuso entregables, hallazgos y una arquitectura proporcional.

**Decisión:** modificar. Acepté la proporcionalidad, pero hice dbt obligatorio y elegí PostgreSQL
para persistencia y serving.

### 2. Semántica y dbt

**Prompt:** “dbt debe dejar de ser opcional y usarse, porque precisamente parte del reto es la capa semántica”.

**Respuesta:** separó contratos, transformación y métricas entre Pydantic, Polars y dbt.

**Decisión:** aceptar con modificación. DuckDB no quedó en el camino principal; dbt es dueño de
conciliación, FX, costos y marts.

### 3. PardoX con paridad

**Prompt:** “PardoX es el motor que yo programé; quiero una alternativa y demostrar su valor”.

**Respuesta:** propuso adaptador, benchmark y paridad con Polars.

**Decisión:** aceptar con restricciones. PardoX procesa `sales.csv` de forma aislada; Polars sigue
siendo referencia y ninguna ruta experimental reemplaza Silver.

### 4. Caso de error: CFDI y criterio de negocio

Este no fue un prompt mío, sino una propuesta de la IA que rechacé.

**Propuesta de Claude:** interpretar `tipo_comprobante` según el SAT: restar E y excluir P/T/N.

**Impacto:** esa regla habría invertido u omitido aproximadamente MXN 1.4 M de ventas.

**Decisión:** la rechacé. El perfilado confirmó cantidades positivas y
precios unitarios superpuestos en los cinco tipos: se cuenta, no se suma ni se resta.

### 5. Carga incremental

**Prompt:** “D1-3: hacer real la carga incremental; prueba altas, modificación, baja y conserva run_id”.

**Respuesta:** distinguió `skipped`, `incremental` y `full` por fuente.

**Decisión:** aceptar con pruebas contra la base real. La etiqueta solo se considera válida cuando
las filas existentes conservan su `run_id`.

## Errores concretos y autocrítica

Los errores detectados fueron: cobertura 100% por contar `sku_erp` nulo como explícito; P1 inflada
unas 40 veces por mezclar red con tienda; RLS declarado pero no aplicado; una carga “incremental”
que recargaba todo; un benchmark PardoX contra una ruta que no hacía trabajo; P4 sin filtro de
ventana, que también escapó inicialmente al revisor; y un refactor de CLI que perdió validaciones.
El patrón fue **declarar en vez de ejecutar**. Cada caso se corrigió con una prueba que podía fallar,
un recálculo independiente o una consulta real.

Mi responsabilidad al 100% son las decisiones de alcance y stack, las interpretaciones de negocio,
la integración de PardoX y el criterio para aceptar o rechazar sugerencias. La IA aportó volumen de
implementación y documentación. Validé más allá de “corre sin error” con recálculo desde fuentes,
controles negativos, paridad SQL, hashes, RLS real y corrida desde clon limpio. El alcance ampliado
también aumentó la superficie de revisión: los problemas de CLI, PardoX y RLS aparecieron en el
endurecimiento, no en el núcleo. Con un plazo estricto recortaría primero dashboards avanzados,
portabilidad y benchmarks secundarios, manteniendo las cuatro respuestas, tests, propuesta y AI_LOG.

El registro cronológico completo está en [docs/BITACORA_IA_DETALLADA.md](docs/BITACORA_IA_DETALLADA.md).
