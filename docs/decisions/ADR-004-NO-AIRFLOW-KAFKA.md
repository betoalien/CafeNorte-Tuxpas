# ADR 004 Defer Airflow and Kafka

## Estado

Aceptada.

## Decision

No usar Airflow ni Kafka en la primera entrega.

## Razon

Las fuentes son batch, el volumen es pequeno, solo hay un pipeline y el presupuesto AWS es cercano a USD 200 mensuales. Docker y scripts cubren reproducibilidad local; EventBridge y Step Functions cubren la orquestacion AWS inicial.

## Triggers de revision

- Multiples DAG y equipos.
- Backfills frecuentes.
- Dependencias complejas y SLA operativos.
- CDC o eventos en tiempo casi real.
- Multiples consumidores y necesidad de replay.

