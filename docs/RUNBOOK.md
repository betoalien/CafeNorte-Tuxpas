# Runbook local

## Contrato operativo

### start.sh

Valida prerrequisitos, construye imagenes, levanta PostgreSQL, Redis y Superset, crea la base separada `superset_meta`, ejecuta contratos, Silver, paridad PardoX, `dbt build`, carga dashboards y evidencia. En local, Superset conecta al schema `analytics` por `psycopg2`; no levanta OAuth, Let's Encrypt ni proxy HTTPS. Debe poder repetirse sin duplicar datos ni regenerar contraseñas existentes.

### stop.sh

Detiene servicios sin borrar datos generados, evidencia ni volumenes.

### restart.sh

Compone `stop.sh` y `start.sh`; no replica sus comandos.

### reset.sh

Elimina solo recursos reproducibles del proyecto. Requiere `--yes`, muestra objetivos exactos y preserva `datos/`, documentos y `AI_LOG.md`.

### validate.sh

Ejecuta contratos, pruebas Python, paridad de motores, `dbt build`, reconciliaciones y controles de privacidad.

### status.sh

Muestra contenedores, healthchecks, ultima corrida, conteos por capa, estado dbt, caché y URL local de Superset.

## Fallos

- Un contrato invalido bloquea la fuente afectada.
- Un registro invalido conocido va a cuarentena si el contrato permite continuar.
- Una diferencia Polars/PardoX bloquea la promocion de PardoX, no el pipeline de referencia.
- Un test dbt critico bloquea Gold.
- Superset no se declara listo si Gold no tiene una ejecucion valida, falla `psycopg2`, RLS no aisla tiendas o el dashboard no fue importado.

## Recuperacion

El pipeline debe reconstruir Silver y Gold desde Bronze. PostgreSQL no es la unica copia de los datos originales. Toda operacion de recuperacion debe registrar un nuevo `run_id`.

