# Evidencia Bloque D1-1

Validación macOS Apple Silicon. No se modificaron PardoX ni la ingesta.

## Validación

```text
./scripts/validate.sh
9 passed
Done. PASS=60 WARN=0 ERROR=0 SKIP=0 TOTAL=60
All checks passed!
```

Redis no publica puerto al host; permanece en la red interna de Compose. Los CSV de respuestas ya
no incluyen `built_at`, por lo que `validate.sh` no ensucia el árbol con timestamps.

## Salida de `superset/test_rls.py`

```text
manager P3 rows=1 channels=T001
manager P4 rows=1 tienda_id=T001
director P3 rows=41 channels=['ONLINE', 'T001', 'T002', 'T003', 'T004', 'T005', 'T006', 'T007', 'T008', 'T009', 'T010', 'T011', 'T012', 'T013', 'T014', 'T015', 'T016', 'T017', 'T018', 'T019', 'T020', 'T021', 'T022', 'T023', 'T024', 'T025', 'T026', 'T027', 'T028', 'T029', 'T030', 'T031', 'T032', 'T033', 'T034', 'T035', 'T036', 'T037', 'T038', 'T039', 'T040']
negative control: director without T001 rule sees 41 channels
dashboard charts=5
Superset API data queries and RLS: PASS
```

El bootstrap idempotente registra la base `CafeNorte analytics`, los cuatro marts más
`mart_source_reconciliation`, y arma el dashboard **CaféNorte — 4 respuestas** con P1 barras top10,
P2 tabla, P3 líneas por canal, P4 tabla y reconciliación tabla.
