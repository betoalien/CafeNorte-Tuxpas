# SPEC 004 Operational harness

## Objetivo

Ofrecer una interfaz de un comando, reproducible y segura para construir, ejecutar, validar y detener la solucion.

## Criterios de aceptacion

```text
Given Docker disponible y las fuentes presentes
When se ejecuta scripts/start.sh
Then se construye una corrida completa y se muestra su estado
```

```text
Given una solucion ya iniciada
When start.sh se ejecuta nuevamente
Then no duplica datos ni crea recursos incompatibles
```

```text
Given reset.sh sin --yes
When se solicita reset
Then no se elimina ningun archivo
```

```text
Given reset.sh --yes
When se limpia el proyecto
Then solo se eliminan salidas reproducibles y datos raw permanecen intactos
```

## Evidencia

- Logs con `run_id`.
- Healthchecks.
- Estado de servicios.
- Resumen de validacion.

