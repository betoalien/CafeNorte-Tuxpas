# Validación del Bloque A-1

Fecha: 2026-10-01 (America/Mexico_City).

## Alcance

Se validaron únicamente perfilado, contratos y harness PostgreSQL. No se crearon tablas Silver,
modelos dbt ni componentes del Bloque B.

## Harness y secretos

Prueba ejecutada desde Windows con Git Bash y Docker Desktop, equivalente al flujo Bash de la
demo Mac:

| Comprobación | Resultado |
|---|---|
| `.env` inexistente al iniciar | `start.sh` lo generó |
| Puerto elegido | `20178`, dentro de 20000–60000 y libre antes del bind |
| Contraseñas | 5 valores distintos de 48 caracteres hex (`openssl rand -hex 24`) |
| SHA-256 de `.env` tras primer arranque | `DB5565F66660ADB5256422DE295222E33179FF627FCB4E74F166EDEE02E21DF2` |
| Segundo `start.sh` | mismo SHA-256 y `POSTGRES_PORT=20178` |
| `restart.sh` | mismo SHA-256 y puerto; PostgreSQL volvió a `healthy` |
| Placeholder | `ENV_FILE=.env.example start.sh` abortó con código 1 por `replace_with` |
| `reset.sh` sin `--yes` | código 2; no realizó cambios |
| `reset.sh --yes` | eliminó contenedor, red y volumen PostgreSQL solamente |

`start.sh` ejecuta `umask 077` y `chmod 600` antes y después del `mv` atómico. NTFS/Git Bash
reporta modo emulado `644`, por lo que el bit POSIX 600 no puede comprobarse en este host; el
comando que lo impone queda activo para macOS/Linux.

`status.sh` mostró:

```text
PostgreSQL host: 127.0.0.1
PostgreSQL port: 20178
Health: healthy
/var/run/postgresql:5432 - accepting connections
```

## Compatibilidad y calidad

- `bash -n` pasó para los seis scripts y el init de PostgreSQL.
- No aparecen `mapfile`, `declare -A`, `${var,,}` ni `sed -i`; el código es compatible con Bash
  3.2 por construcción.
- ShellCheck no estaba instalado y `validate.sh` lo informó como chequeo opcional omitido.
- `uv run ruff check scripts/profile_sources.py`: `All checks passed!`.
- `uv run python scripts/profile_sources.py` regeneró
  [profiling.md](profiling.md) sin errores.
- Compose validó los schemas `silver`, `audit`, `intermediate`, `analytics`; los roles `pipeline`,
  `dbt`, `superset_ro`, `superset_meta`; y la base `superset_meta`.

## Inmutabilidad de `datos/`

Los SHA-256 antes del ciclo start/restart/reset y después de `reset.sh --yes` fueron idénticos:

| Archivo | SHA-256 antes y después |
|---|---|
| `ecommerce_orders.parquet` | `00C560B39425FE7F0088FBE20C66C2B8861D10C2C7006BA6E7335CDD6DFC856E` |
| `exchange_rates.csv` | `A0E827EC1E048CF397584ECA3D692CB5B5B1F6B477FB78EFCA2FDBD2F488BDDF` |
| `inventory.json` | `2355C6CAB9FF00A707B5505A464A8F7E1A9BF5A2AA6C7A2B6B008F5299C8EADA` |
| `sales.csv` | `87628A584D30A353F3BCC9DBE20C2D8F1E55C80A0036ECEE88E76FCE61031276` |

## Estado final

El reset confirmado dejó contenedor y volumen PostgreSQL eliminados. `.env` permanece ignorado y
estable para que el siguiente `start.sh` reutilice el puerto y credenciales; ningún secreto se
incluye en esta evidencia.

## Revalidación en macOS

Fecha: 2026-10-01 (America/Monterrey). Host: macOS con Docker Compose v5.1.1 y `uv` 0.10.5.

Se ejecutó `./scripts/start.sh` desde un checkout migrado desde Windows. La primera ejecución creó
`.env` local ignorado por Git, seleccionó `POSTGRES_PORT=23779`, descargó
`postgres:16.4-alpine3.20`, creó el volumen `cafenorte_postgres_data` y dejó
`cafenorte-postgres` en estado `healthy`.

La primera ejecución de `./scripts/validate.sh` en macOS falló porque ShellCheck sí estaba
instalado en este host y reportó SC2251 en tres negaciones de `port_is_free` dentro de
`scripts/start.sh`; en la validación Windows ese control se había omitido por falta de ShellCheck.
Se reescribieron esas ramas sin cambiar la semántica: si el puerto está ocupado se devuelve 1, si
está libre se devuelve 0.

La segunda ejecución de `./scripts/validate.sh` pasó con:

```text
schema_name: analytics, audit, intermediate, silver
rolname: dbt, pipeline, superset_meta, superset_ro
datname: superset_meta
Ruff: All checks passed!
```

`./scripts/status.sh` confirmó:

```text
PostgreSQL host: 127.0.0.1
PostgreSQL port: 23779
Health: healthy
/var/run/postgresql:5432 - accepting connections
```
