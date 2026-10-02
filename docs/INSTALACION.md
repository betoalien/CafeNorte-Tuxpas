# Instalación y operación

## Requisitos

| Herramienta | Uso | Versión |
|---|---|---|
| Git | Clonar el repositorio | Reciente |
| Docker + Compose v2 | PostgreSQL, Redis y Superset | Docker Engine 24+ o Docker Desktop |
| uv | Entorno reproducible | 0.4+ |
| OpenSSL | Compatibilidad con el harness Bash | Reciente |
| Bash | Envoltorios oficiales | 3.2+ |
| ShellCheck | Validación de scripts | Reciente |

`uv sync` instala Python 3.12. En macOS instala herramientas de línea de comandos,
Homebrew, `uv` y ShellCheck; Docker Desktop debe mostrar Engine running. En Ubuntu,
instala Git, OpenSSL, ShellCheck, `iproute2`, Docker Engine/Compose v2 y uv. En Fedora
usa los paquetes equivalentes y habilita el daemon Docker.

Windows nativo requiere Docker Desktop en Linux containers, Git y uv (`winget install
astral-sh.uv` o el instalador oficial):

```powershell
uv sync
uv run cafenorte start
uv run cafenorte validate
```

Los `.bat` de `scripts/windows/` son equivalentes. WSL2 es una alternativa: clona dentro
del filesystem Linux, no bajo `/mnt/c`, porque allí permisos 600, finales de línea y
rendimiento de Docker pueden cambiar.

## Tres comandos

```bash
git clone <repositorio>
cd CafeNorte-Tuxpas
./scripts/start.sh
./scripts/validate.sh
```

También existe `uv run cafenorte start|stop|restart|status|validate|reset|credentials|doctor|report`.
`reset --yes` limpia volúmenes, pero nunca `datos/`, contratos ni documentación.

## Dashboards y credenciales

`start.sh` muestra la URL real de Superset, el dashboard `CaféNorte — 4 respuestas`,
los usuarios y `artifacts/reports/run_report.html`. `./scripts/credentials.sh` muestra
contraseñas solo bajo solicitud; también se puede usar `start.sh --show-credentials`.
Las credenciales locales viven en `.env`, protegido con 600 en macOS/Linux y con ACL
del usuario actual mediante `icacls` en Windows.

## Plataformas probadas

- macOS arm64: validación manual completa; PardoX soportado y probado.
- macOS x86_64: binario PardoX incluido, no verificado en CI; si no carga, se reporta unsupported.
- Ubuntu x86_64: flujo completo en GitHub Actions.
- WSL2: Ubuntu x86_64, con repo dentro del filesystem Linux.
- Windows nativo: flujo soportado, no verificado con Docker en CI.
- Linux arm64: Polars funciona; PardoX no está disponible y no tumba el pipeline principal.

En Apple Silicon, Python bajo Rosetta reporta x86_64; usa el Python arm64 instalado por uv.

## Problemas comunes

- Si Docker no responde, inicia Docker Desktop o el daemon y vuelve a ejecutar `doctor`.
- Si falta ShellCheck, instálalo: `brew install shellcheck` o el paquete de tu distribución.
- Si WSL detecta CRLF o el repo está bajo `/mnt/`, clónalo de nuevo dentro de Linux.
- Los originales se verifican con `cd datos && shasum -a 256 -c SHA256SUMS` en macOS o
  `sha256sum -c SHA256SUMS` en Linux. Si falla, aparece `fuente original del cliente modificada`.
- Si PardoX no tiene binario para la plataforma, validate informa
  `PardoX: UNSUPPORTED_PLATFORM (<os>-<arch>)` y valida Polars, dbt y Superset normalmente.

## Datos nuevos

`skipped`: todos los hashes coinciden, no se toca Silver ni se corre dbt. `incremental`:
solo claves nuevas se insertan. `full`: se reemplaza la tabla de la fuente si hay cambios
en filas existentes o desapariciones. `CAFENORTE_DATA_DIR` permite probar una copia temporal.
