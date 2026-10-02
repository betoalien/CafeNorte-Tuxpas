# Validación D3-8

- P3 agregado: mart `analytics.mart_monthly_channel_type_growth`, 24 filas, 12 por `FISICO`/`ECOMMERCE`.
- Test dbt del agregado y suma contra detalle: PASS.
- dbt completo posterior al ajuste: `PASS=65 WARN=0 ERROR=0 SKIP=0`.
- pytest previo al ajuste documental: `23 passed`; la suite documental agrega enlaces y cifras certificadas.
- Ruff: PASS después de retirar cabeceras `ruff: noqa`.
- Propuesta AWS revisada a máximo dos páginas de contenido; el entorno no tenía motor PDF instalado para exportarla automáticamente.
