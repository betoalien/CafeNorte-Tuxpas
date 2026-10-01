# CaféNorte Data Platform Challenge

## Estado

Proyecto en fase de especificación. La arquitectura, los contratos y los criterios de aceptación están definidos; el pipeline aún no está implementado.

## Objetivo

Crear una fuente analítica confiable para ventas e inventario de CaféNorte y responder:

1. Top 10 SKU por rotación de inventario en los últimos seis meses.
2. Tiendas con quiebres de stock mayores a tres días en el último trimestre.
3. Crecimiento mensual de ventas por canal durante el último año.
4. Productos con margen negativo y las tiendas donde ocurren.

## Arquitectura local decidida

```text
Fuentes inmutables
        |
Contratos Pydantic
        |
Polars (referencia) / PardoX (alternativa verificada)
        |
PostgreSQL Silver
        |
dbt: intermedia, dimensiones, hechos y marts
        |
PostgreSQL Gold
        |
Apache Superset
```

Polars y PardoX realizan la preparación columnar. PostgreSQL persiste y sirve los datos. dbt es propietario de las reglas de negocio y la capa semántica materializada. Superset consulta únicamente Gold mediante `psycopg2` y aplica RLS por tienda.

## Capas

- **Bronze:** archivos originales y manifiestos; nunca se modifican.
- **Silver:** entidades técnicamente normalizadas y PII excluida.
- **Gold:** dimensiones, hechos, métricas y marts certificados por dbt.
- **Audit:** cuarentena, reconciliaciones, calidad y ejecuciones.

## Documentación

- `docs/SYSTEM_MAP.md`: mapa conceptual.
- `docs/DATA_CONTRACTS.md`: contratos de fuentes y capas.
- `docs/BUSINESS_METRICS.md`: definiciones de métricas.
- `docs/IMPLEMENTATION_PLAN.md`: fases y gates.
- `docs/specs/`: especificaciones verificables.
- `docs/decisions/`: decisiones arquitectónicas.
- `docs/RUNBOOK.md`: contrato operativo.
- `AI_LOG.md`: bitácora obligatoria de uso de IA.

## Datos

La carpeta `datos/` contiene tres fuentes operacionales y un dataset auxiliar de tipos de cambio. Son datos sintéticos proporcionados para el reto y se publican como parte de este repositorio. Aunque no representan personas reales, el pipeline trata los campos de identificación como PII y los excluye de Silver y Gold.

## Ejecución prevista

```bash
./scripts/start.sh
./scripts/validate.sh
./scripts/status.sh
./scripts/stop.sh
```

El Bloque A implementa estos comandos para PostgreSQL. En el primer `start.sh`, `.env` se genera
con secretos aleatorios y un puerto libre entre 20000 y 60000; los reinicios posteriores reutilizan
exactamente esa configuración.

## Interpretaciones

Estas reglas fueron cerradas por el propietario a partir de la
[evidencia de perfilado](artifacts/evidence/profiling.md#interpretaciones-cerradas-por-el-propietario):

1. `tipo_comprobante` es un atributo del CFDI. Todas las filas son ventas; el CFDI se cuenta por
   tipo y nunca hace que monto o cantidad se sumen, resten o excluyan de forma distinta.
2. La conciliación usa mapping explícito primero y número de producto con nombre validado como
   respaldo. `match_method` será `explicit` o `product_number`; lo no conciliado va a Audit.
3. `monto` se supone neto sin IVA: no hay campo de impuesto y las categorías tienen tasas 0%/16%.
4. `tiendas_info` del ERP es el maestro. Sus diferencias contra el relato del cliente se reportan.
5. FX usa la tasa del día. EUR=22.0 se usa con `fx_quality_flag` por posible truncamiento.
6. P2 lista una tienda si algún SKU tuvo más de tres días consecutivos con stock cero; `N/A`
   rompe la secuencia. Se conserva SKU, inicio, fin y días.
7. P4 reporta POS por tienda y e-commerce como canal `ONLINE`.
8. Las ventanas se anclan en 2026-03-31. Inventario cubre exactamente seis meses y el MoM de
   e-commerce de 2025-04 queda `null` por falta de base.
9. Gold incluirá un mart de reconciliación que explique diferencias entre POS, ERP y Shopify.

