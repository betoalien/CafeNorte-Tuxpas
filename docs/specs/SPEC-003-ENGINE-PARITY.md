# SPEC 003 Polars and PardoX parity

## Objetivo

Demostrar que PardoX puede ejecutar la ruta acordada con resultados equivalentes a Polars antes de comparar rendimiento.

## Alcance inicial

- `sales.csv`.
- Lectura, tipado, controles, agregaciones y carga PostgreSQL.
- Persistencia `.prdx` como demostracion.

## Restricciones

- Solo se usan capacidades de la version publicada y fijada.
- Polars es el oraculo de referencia del reto, no una prueba absoluta de verdad.
- Diferencias de orden no cuentan si el contrato no exige orden.

## Criterios de aceptacion

```text
Given la misma fuente y contrato
When Polars y PardoX procesan sales.csv
Then coinciden filas, claves, nulos, sumas y agregaciones acordadas
```

```text
Given una diferencia de paridad
When se ejecuta validate
Then PardoX no se promueve a Silver y se conserva evidencia de la diferencia
```

## Rendimiento

Se mide despues de paridad: cold read, transformacion, carga, tiempo total, memoria y tamano de salida. No se generalizan resultados del dataset pequeno a cargas grandes.

