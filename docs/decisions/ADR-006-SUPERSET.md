# ADR 006: Apache Superset como visor

## Estado

Aceptada.

## Contexto

El reto necesita dashboards reproducibles, control por tienda y una experiencia que el cliente pueda abrir al ejecutar el Docker final. La capa de presentación no debe redefinir métricas: consume exclusivamente Gold certificado por dbt.

## Decisión

Usar Apache Superset como visor principal. Docker Compose local incluye Superset y Redis; los metadatos se guardan en la base separada `superset_meta` dentro de la misma instancia PostgreSQL. Los dashboards y roles se versionan, y el arranque crea credenciales iniciales desde secretos externos.

Las versiones locales quedan fijadas en `apache/superset:4.1.1` y `redis:7.2.7-alpine3.21`; ambas
son imágenes multi-arquitectura con `linux/arm64`. `start.sh` genera el puerto de Superset, la
clave secreta y las contraseñas demo en `.env` con `openssl rand`.

`admin` conserva el rol administrativo; `director` usa un rol propio con acceso completo a los
datasets Gold, y `gerente_t001` usa Gamma más su rol propio sin Alpha ni SQL Lab. `DIRECTOR_PASSWORD`
se genera junto con las demás credenciales.

- **Local:** Superset conecta mediante `psycopg2` al schema PostgreSQL `analytics` con usuario de solo lectura. RLS limita al gerente a su tienda y permite a dirección consultar todas. La demo usa autenticación local; no incorpora OAuth, Let's Encrypt ni proxy HTTPS.
- **Producción AWS:** Superset conecta a Athena mediante PyAthena y usa Redis para caché. Se habilitan OAuth Google/Microsoft, HTTPS/443 con Let's Encrypt y RLS equivalente.

## Alternativas consideradas

| Alternativa | Decisión y razón |
|---|---|
| QuickSight | Ruta de salida administrada si el cliente no quiere operar Superset; se rechaza como principal por costo por usuario. |
| Streamlit | Rechazado como visor principal: exigiría construir navegación, permisos, RLS y administración que Superset ya ofrece. |
| Tableau | Bonus opcional; requiere licencias separadas y no forma parte del camino reproducible del reto. |

## Consecuencias y riesgos

- Superset no tiene costo de licencia por usuario, pero TI o Tuxpas asume parches, monitoreo y backups de metadatos.
- La propuesta inicial usa una sola instancia Lightsail de 4 GB: no existe alta disponibilidad y una falla interrumpe el visor.
- Los snapshots no sustituyen el backup lógico de `superset_meta` ni una prueba de restauración.
- Si CPU o memoria supera 70% sostenido, el p95 excede 10 segundos o falla la prueba de concurrencia, se escala la instancia o se separan metadatos/caché.
- QuickSight permanece como migración posible si el costo operativo supera el beneficio del precio fijo.
