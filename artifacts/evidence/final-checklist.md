# Checklist final

Definition of Done de `AGENTS.md`:

- [x] Contratos Pydantic y manifests: [`block-b1-validation.md`](block-b1-validation.md), [`DATA_CONTRACTS.md`](../../docs/DATA_CONTRACTS.md).
- [x] Polars produce Silver y rechazos: [`block-b-validation.md`](block-b-validation.md).
- [x] Ruta PardoX y paridad: [`block-d2-5-validation.md`](block-d2-5-validation.md) y [repro PRDX](pardox-0.3.4-prdx-repro/README.md).
- [x] dbt genera y prueba Gold: [`block-c-validation.md`](block-c-validation.md) y `dbt/run_results.json`.
- [x] Cuatro respuestas con consultas y evidencia: [`answers/README.md`](answers/README.md).
- [x] Documentación y lineage: [`SYSTEM_MAP.md`](../../docs/SYSTEM_MAP.md), [`RUNBOOK.md`](../../docs/RUNBOOK.md) y [`AI_LOG.md`](../../AI_LOG.md).
- [x] Docker reproduce el flujo desde entorno limpio: [`final-validation.md`](final-validation.md).
- [x] AWS, costos y supuestos documentados: [`PROPUESTA_AWS.md`](../../docs/PROPUESTA_AWS.md).
- [x] No se publican secretos ni PII: controles de seguridad en [`final-validation.md`](final-validation.md).

La única limitación no silenciosa es `write_sql_prdx` a x10: queda excluido de la ruta certificada
y enlazado a su reproducción; no invalida Polars ni PardoX `to_sql`.
