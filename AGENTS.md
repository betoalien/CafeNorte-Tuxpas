# Instrucciones del repositorio CafeNorte

## Autoridad y adopcion

Este repositorio adopta `UNIVERSAL_ARCHITECTURE.md` como metodologia obligatoria de trabajo. La solicitud vigente del propietario, el reto tecnico y las especificaciones de `docs/specs/` tienen precedencia conforme a la jerarquia definida en ese documento.

## Objetivo

Construir una solucion reproducible de ingenieria de datos que ingiera las fuentes de CafeNorte, preserve su trazabilidad, modele metricas de negocio con dbt y responda las cuatro preguntas del reto. La solucion local debe ejecutarse en Docker y tener una ruta clara de evolucion a AWS dentro del presupuesto indicado.

## Invariantes

- Los archivos originales de `datos/` son inmutables y se montan como solo lectura.
- Ningun registro invalido se elimina silenciosamente; se conserva o se envia a cuarentena con motivo.
- `N/A` en inventario significa desconocido, no stock cero.
- La PII de Shopify no llega a modelos Silver analiticos ni Gold.
- Polars es el motor de referencia. PardoX es un motor alternativo cuya salida debe demostrar paridad antes de promoverse.
- dbt es el propietario de conciliacion de negocio, modelo dimensional, metricas y marts.
- PostgreSQL es el almacen local y serving layer; el dashboard solo consulta objetos Gold certificados.
- Los resultados no se consideran correctos solamente porque el proceso termine sin error.
- No se guardan secretos, credenciales ni archivos `.env` reales en el repositorio.
- Ningun script de reset puede eliminar `datos/`, documentacion, contratos ni `AI_LOG.md`.

## Flujo obligatorio

1. Leer la especificacion y los ADR aplicables.
2. Confirmar criterios de aceptacion y supuestos.
3. Mantener el cambio dentro del alcance acordado.
4. Ejecutar los comandos oficiales aplicables.
5. Guardar evidencia reproducible en `artifacts/evidence/`.
6. Actualizar `AI_LOG.md` durante el trabajo, no retrospectivamente al final.

## Comandos oficiales previstos

Estos comandos son parte del contrato operativo y se implementaran antes de declarar el pipeline completo:

```bash
./scripts/start.sh
./scripts/stop.sh
./scripts/restart.sh
./scripts/reset.sh --yes
./scripts/validate.sh
./scripts/status.sh
```

Hasta que existan, ningun documento debe afirmar que ya fueron ejecutados.

## Definition of Done

Una entrega solo esta terminada cuando:

- los contratos Pydantic validan las entradas y manifests;
- Polars produce Silver y registra rechazos;
- la ruta PardoX acordada pasa pruebas de paridad;
- `dbt build` genera y prueba Gold;
- las cuatro respuestas tienen consultas y evidencia;
- la documentacion y el lineage coinciden con la implementacion;
- Docker reproduce el flujo desde un entorno limpio;
- no se publica PII ni secretos;
- el costo y los supuestos AWS estan documentados;
- `AI_LOG.md` contiene prompts, decisiones, correcciones y autocritica reales.

