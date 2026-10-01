# UNIVERSAL_ARCHITECTURE.md

## 1. Propósito

Este documento define la metodología universal de ingeniería para los proyectos que lo adopten. Su objetivo es hacer que el desarrollo sea repetible, verificable y seguro, especialmente cuando se utilicen agentes de inteligencia artificial para analizar, planear, implementar, probar o revisar cambios.

Este documento define el **cómo trabajar**. No define el framework, proveedor cloud, lenguaje, estructura de carpetas ni arquitectura concreta de un proyecto. Esas decisiones pertenecen a la documentación específica de cada repositorio.

## 2. Ámbito y precedencia

Todo proyecto que adopte este documento debe declarar su adopción en su `AGENTS.md` local.

La jerarquía de autoridad es:

1. Solicitud explícita y vigente del propietario del proyecto.
2. `AGENTS.md` aplicable al repositorio.
3. Alcance contractual aprobado, cuando exista.
4. Requisitos, especificaciones y criterios de aceptación.
5. Decisiones arquitectónicas registradas.
6. Este documento universal.
7. Convenciones existentes del código.

Una excepción a esta metodología debe estar documentada, tener responsable y explicar su impacto. No se deben crear excepciones silenciosas dentro del código.

## 3. Principios obligatorios

- El comportamiento esperado debe estar especificado antes de implementarse.
- Toda funcionalidad debe tener criterios de aceptación verificables.
- La seguridad, privacidad, accesibilidad, observabilidad y operación forman parte del diseño inicial.
- El agente debe trabajar con contexto suficiente, pero no con contexto innecesario.
- El cambio debe ser pequeño, trazable y reversible cuando sea posible.
- El código no puede convertirse en la fuente exclusiva de la verdad del producto.
- Ningún agente puede inventar requisitos, usuarios, permisos, datos, secretos o decisiones pendientes.
- Una tarea no está terminada porque el código compile; está terminada cuando existe evidencia de que cumple su contrato.
- Los problemas fuera del alcance deben registrarse, no incorporarse silenciosamente.

## 4. Harness Engineering

Harness Engineering significa construir el entorno que permite al agente trabajar dentro de límites claros. Cada proyecto debe proporcionar, según corresponda:

- instrucciones permanentes del repositorio;
- mapa conceptual del sistema;
- documentos de requisitos y decisiones;
- contratos de interfaces;
- datos de prueba determinísticos;
- comandos oficiales de validación;
- revisores especializados;
- reglas de seguridad y privacidad;
- criterios de release y rollback.

El objetivo es que la calidad no dependa de repetir manualmente el contexto en cada conversación.

Los agentes deben operar con permisos mínimos. Un agente de revisión debe ser de solo lectura salvo autorización explícita para editar. Un agente implementador no debe desplegar ni modificar infraestructura productiva como consecuencia implícita de una tarea de código.

## 5. Spec-Driven Development

Toda tarea funcional, técnica o de seguridad debe comenzar con una especificación breve y trazable.

Como mínimo debe declarar:

- identificador estable;
- objetivo;
- problema que resuelve;
- alcance incluido;
- alcance excluido;
- actores y permisos involucrados;
- reglas de negocio;
- criterios de aceptación;
- errores esperados;
- impacto en datos y contratos;
- restricciones de seguridad;
- dependencias y decisiones pendientes;
- evidencia y comandos de validación.

Si faltan datos esenciales, la tarea debe marcarse como bloqueada o solicitar una decisión. No se deben completar vacíos con suposiciones no registradas.

## 6. Specification by Example

Los criterios de aceptación deben utilizar ejemplos concretos, preferentemente con la forma:

```text
Given una condición inicial
When ocurre una acción
Then se obtiene un resultado observable
```

Los ejemplos deben cubrir tanto el camino exitoso como los caminos prohibidos, inválidos, expirados, duplicados y fallidos cuando sean relevantes.

Ejemplo:

```text
Given un usuario de la organización A
When solicita un recurso perteneciente a la organización B
Then la API no revela el recurso ni sus datos
```

## 7. Decisiones arquitectónicas

Las decisiones importantes deben registrarse en documentos breves y estables. Cada decisión debe contener:

- contexto;
- problema;
- decisión adoptada;
- alternativas consideradas;
- consecuencias positivas y negativas;
- riesgos;
- alcance afectado;
- estado;
- decisiones que reemplaza o que podrían reemplazarla.

Una decisión histórica no debe borrarse para ocultar su evolución. Si cambia, debe registrarse una nueva decisión que la reemplace.

## 8. Contratos e interfaces

Toda comunicación entre componentes debe tener un contrato explícito cuando el proyecto lo permita:

- API HTTP;
- eventos;
- colas;
- archivos;
- mensajes;
- integraciones externas;
- respuestas de error;
- permisos y límites.

El contrato debe definir nombres, tipos, formatos, validaciones, errores, compatibilidad y versionado. Las implementaciones deben ajustarse al contrato. No se deben modificar interfaces públicas accidentalmente durante una tarea interna.

## 9. Invariantes del sistema

Cada proyecto debe declarar las reglas que nunca pueden romperse. Como mínimo deben considerarse:

- ningún actor accede a datos sin autorización;
- ningún secreto se guarda en el repositorio;
- las migraciones no destruyen datos sin autorización explícita;
- los errores no filtran información sensible;
- las operaciones críticas dejan evidencia suficiente;
- los estados transaccionales no quedan parcialmente aplicados;
- las integraciones externas tienen timeout, reintento controlado y manejo de fallos;
- las versiones derivadas no modifican silenciosamente el núcleo de la versión maestra;
- una release no se promueve si falla una prueba crítica o existe un hallazgo bloqueante.

Los invariantes deben convertirse en pruebas o revisiones automatizadas siempre que sea posible.

## 10. Seguridad universal

Todo proyecto web debe revisar sus riesgos contra OWASP Top 10:2025:

1. `A01:2025` Broken Access Control.
2. `A02:2025` Security Misconfiguration.
3. `A03:2025` Software Supply Chain Failures.
4. `A04:2025` Cryptographic Failures.
5. `A05:2025` Injection.
6. `A06:2025` Insecure Design.
7. `A07:2025` Authentication Failures.
8. `A08:2025` Software or Data Integrity Failures.
9. `A09:2025` Security Logging and Alerting Failures.
10. `A10:2025` Mishandling of Exceptional Conditions.

La revisión debe traducir cada categoría aplicable en requisitos, controles y pruebas. OWASP Top 10:2025 es una referencia de riesgos generales de aplicaciones web; cuando el proyecto exponga APIs se deben incorporar también los controles específicos del estándar API Security correspondiente.

Como mínimo, toda aplicación debe analizar:

- autenticación y sesiones;
- autorización por acción y recurso;
- aislamiento entre organizaciones o tenants;
- validación de entradas y salidas;
- inyección;
- secretos y criptografía;
- configuración de ambientes;
- dependencias y cadena de suministro;
- integridad de archivos, eventos y artefactos;
- logs, auditoría y alertas;
- límites, timeouts, reintentos y errores;
- respaldo, restauración y continuidad operativa.

La seguridad no es una etapa final. Cada especificación debe indicar sus riesgos y controles relevantes.

## 11. Datos y privacidad

Antes de implementar una entidad o flujo se debe identificar:

- propietario del dato;
- propósito;
- clasificación de sensibilidad;
- ciclo de vida;
- retención;
- acceso permitido;
- auditoría requerida;
- eliminación o anonimización;
- respaldo y restauración.

No se deben utilizar datos reales en pruebas, fixtures, capturas, logs o ambientes de desarrollo salvo autorización documentada y controles adecuados.

## 12. Flujo universal de una tarea

### 12.1 Ready

Una tarea está lista cuando tiene especificación, alcance, criterios de aceptación, dependencias, restricciones y validación definida.

### 12.2 Plan

Antes de modificar archivos, el agente debe identificar:

- archivos o componentes probablemente afectados;
- cambios que no realizará;
- decisiones que debe respetar;
- pruebas necesarias;
- supuestos explícitos;
- posibles bloqueos.

### 12.3 Implementación

La implementación debe mantenerse dentro del alcance y presupuesto de cambio. No se deben introducir refactorizaciones, dependencias, migraciones o cambios de infraestructura no necesarios para cumplir la especificación.

### 12.4 Validación

El agente debe ejecutar los comandos relevantes y revisar comportamiento exitoso, comportamiento inválido, autorización, regresiones y seguridad.

### 12.5 Revisión

La revisión debe producir hallazgos con identificador, severidad, evidencia, impacto, recomendación y condición de bloqueo.

### 12.6 Cierre

Una tarea solo puede cerrarse cuando el resultado, las pruebas, la evidencia, la documentación y los pendientes están registrados.

## 13. Definition of Ready

Antes de iniciar una tarea debe existir:

- objetivo comprensible;
- alcance y fuera de alcance;
- actores y permisos;
- criterios de aceptación;
- contrato afectado, si aplica;
- datos de prueba;
- riesgos de seguridad;
- dependencias;
- decisión de validación;
- responsable de aceptación.

## 14. Definition of Done

Una tarea terminada debe cumplir:

- implementación alineada con la especificación;
- pruebas relevantes ejecutadas;
- errores y permisos verificados;
- contratos actualizados o confirmados;
- migraciones revisadas;
- documentación actualizada;
- secretos y datos sensibles ausentes;
- revisiones necesarias completadas;
- evidencia guardada;
- limitaciones y pendientes declarados.

## 15. Pruebas y evidencia

La estrategia de pruebas debe cubrir, según el riesgo:

- unidad;
- integración;
- contrato;
- autorización y aislamiento;
- flujos completos;
- accesibilidad;
- rendimiento;
- migraciones;
- seguridad;
- despliegue;
- respaldo y restauración.

Las pruebas negativas son obligatorias para controles de seguridad. No basta demostrar que un usuario autorizado puede hacer algo; también debe demostrarse que un usuario no autorizado no puede hacerlo.

Toda afirmación de “listo”, “seguro”, “aceptado” o “desplegable” debe estar respaldada por evidencia reproducible.

## 16. Revisiones especializadas

Cuando el proyecto lo requiera, deben participar revisores independientes de:

- arquitectura;
- seguridad;
- calidad y aceptación;
- datos;
- operación o despliegue.

Los revisores deben priorizar hallazgos reales sobre recomendaciones cosméticas y no deben aprobar por intuición. Un hallazgo crítico o alto sin mitigación bloquea la release salvo excepción aprobada.

## 17. Presupuesto de cambio

Cada tarea debe limitar, cuando sea posible:

- número de archivos modificados;
- módulos afectados;
- migraciones creadas;
- dependencias agregadas;
- contratos modificados;
- cambios de infraestructura.

Si la implementación supera significativamente el presupuesto, el agente debe detenerse, explicar la causa y proponer dividir la tarea. No debe ampliar el alcance por iniciativa propia.

## 18. Eficiencia de contexto y tokens

Los proyectos deben reducir contexto repetido mediante:

- un mapa conceptual del repositorio;
- especificaciones pequeñas por tarea;
- decisiones persistentes;
- contratos reutilizables;
- fixtures determinísticos;
- comandos oficiales de validación;
- registro de contradicciones;
- skills especializadas para flujos repetibles.

El agente debe leer primero las instrucciones aplicables, después el spec y solo los archivos directamente relacionados. No debe cargar todo el repositorio por defecto.

Una tarea bien preparada debe poder ejecutarse con este paquete mínimo:

```text
Objetivo
Contexto
Restricciones
Archivos relevantes
Criterios de aceptación
Pruebas requeridas
Comando de validación
```

## 19. Contradicciones y decisiones pendientes

Cuando dos fuentes discrepen, el agente debe:

1. identificar las fuentes;
2. explicar la contradicción;
3. indicar qué funcionalidades afecta;
4. proponer la opción más segura y de menor impacto;
5. detener la parte bloqueada si no puede decidirse legítimamente;
6. registrar la decisión o excepción.

Nunca se debe resolver una contradicción solamente mediante una elección oculta en el código.

## 20. Releases y promoción

Una release debe tener:

- versión identificable;
- alcance documentado;
- pruebas ejecutadas;
- revisión de seguridad;
- revisión de regresiones;
- migraciones verificadas;
- instrucciones de despliegue;
- estrategia de rollback;
- evidencia de aceptación.

Las versiones derivadas de un producto maestro deben registrar exactamente la versión de origen. Una personalización útil para más de un cliente debe regresar primero al producto maestro y después promoverse mediante una nueva versión estable.

## 21. Reglas para agentes de inteligencia artificial

- Leer las instrucciones aplicables antes de actuar.
- No inventar requisitos ni datos.
- No modificar archivos no relacionados sin justificarlo.
- No eliminar protecciones, pruebas o validaciones para hacer pasar una tarea.
- No ocultar errores de pruebas o comandos fallidos.
- No declarar éxito sin evidencia.
- Pedir aclaración cuando una decisión cambie seguridad, alcance, datos, costo o compatibilidad.
- Reportar supuestos antes de implementarlos.
- Preferir cambios pequeños y reversibles.
- Dejar el repositorio en un estado comprensible para el siguiente agente o desarrollador.

## 22. Excepciones específicas del proyecto

Cada repositorio puede adaptar esta metodología, pero debe documentar:

- la regla universal afectada;
- la excepción adoptada;
- el motivo;
- el riesgo;
- el responsable de aprobación;
- la fecha de revisión;
- las pruebas o controles compensatorios.

Una excepción no convierte automáticamente una práctica local en estándar universal.

## 23. Registro de versiones

### [Unreleased]

- Documento universal inicial para proyectos con desarrollo guiado por especificaciones y agentes de inteligencia artificial.
- Incorporación de Harness Engineering, Spec-Driven Development y Specification by Example.
- Incorporación de OWASP Top 10:2025 como marco universal de riesgos web.
- Definición de reglas de contexto, tokens, revisiones, pruebas, evidencia y promoción.
