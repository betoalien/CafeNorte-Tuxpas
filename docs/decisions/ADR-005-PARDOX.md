# ADR 005 PardoX as alternative engine

## Estado

Aceptada.

## Contexto

PardoX es un motor DataFrame con nucleo Rust desarrollado por el propietario. Su inclusion demuestra diseno de motores, portabilidad y criterio single-node.

## Decision

Polars es la implementacion de referencia. PardoX implementa una ruta alternativa limitada a capacidades publicadas y se promueve solo cuando pasa paridad.

## Consecuencias

- Se fija la version de PardoX.
- Se genera evidencia de paridad antes de benchmarks.
- Se documentan limitaciones actuales.
- Una falla de PardoX no invalida la ruta Polars, pero si bloquea cualquier afirmacion de equivalencia.

