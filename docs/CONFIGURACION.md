# Configuración y operación paso a paso

Esta guía lleva el proyecto desde una máquina limpia hasta el dashboard funcionando. Elige tu
sistema operativo, sigue sus pasos y después continúa con
[Instalación (todas las plataformas)](#instalación-todas-las-plataformas).

- [Requisitos](#requisitos)
- [macOS](#macos-intel-o-apple-silicon)
- [Windows nativo (PowerShell)](#windows-1011-nativo-powershell)
- [Windows con WSL2](#windows-1011-con-wsl2)
- [Ubuntu / Debian](#ubuntu--debian)
- [Fedora / RHEL / Rocky / Alma](#fedora--rhel--rocky--alma)
- [Instalación (todas las plataformas)](#instalación-todas-las-plataformas)
- [Qué esperar al arrancar](#qué-esperar-al-arrancar)
- [Ver los dashboards](#ver-los-dashboards)
- [Comandos disponibles](#comandos-disponibles)
- [Cuando llegan datos nuevos](#cuando-llegan-datos-nuevos)
- [Plataformas probadas](#plataformas-probadas)
- [Problemas comunes](#problemas-comunes)

## Requisitos

| Herramienta | Para qué se usa | Versión |
|---|---|---|
| Git | Clonar el repositorio | Cualquiera reciente |
| Docker + Docker Compose v2 | PostgreSQL, Redis y Superset | Docker Engine 24+ o Docker Desktop |
| uv | Entorno de Python reproducible (`uv.lock`) | 0.4+ (instala Python 3.12 por sí mismo) |
| ShellCheck | Validación de los scripts en `validate` | Cualquiera reciente (no aplica en Windows nativo) |

No hace falta instalar Python a mano: `uv sync` descarga Python 3.12 si no está presente. Las
contraseñas y los puertos se generan solos la primera vez; no hay nada que configurar a mano.

Antes de arrancar puedes comprobar tu entorno con `./scripts/doctor.sh` (o
`scripts\windows\doctor.bat`): revisa Docker, Compose, uv, ShellCheck, la arquitectura y si
PardoX tiene binario para tu plataforma, y te dice cómo resolver lo que falte.

## macOS (Intel o Apple Silicon)

```bash
# 1. Herramientas de línea de comandos (incluye Git)
xcode-select --install

# 2. Homebrew, si no lo tienes: https://brew.sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 3. Dependencias
brew install uv shellcheck

# 4. Docker Desktop (elige la versión Apple Silicon o Intel)
#    https://www.docker.com/products/docker-desktop/
#    Ábrelo una vez y espera a que diga "Engine running".
docker compose version
```

En Apple Silicon usa el Python arm64 que instala `uv`. Un Python antiguo corriendo bajo Rosetta
reporta `x86_64` y cargaría binarios Intel.

## Windows 10/11 nativo (PowerShell)

1. Instala [Docker Desktop para Windows](https://www.docker.com/products/docker-desktop/) y
   déjalo en modo **Linux containers** (el predeterminado). Ábrelo y espera a "Engine running".
2. En PowerShell:

   ```powershell
   winget install --id Git.Git -e
   winget install --id astral-sh.uv -e
   # Cierra y vuelve a abrir PowerShell para que tome el PATH
   docker compose version
   uv --version
   ```

3. Usa los scripts de `scripts\windows\`: `start.bat`, `stop.bat`, `restart.bat`,
   `status.bat`, `validate.bat`, `reset.bat`, `credentials.bat` y `doctor.bat`. Funcionan desde
   cmd, PowerShell o con doble clic, y llaman a la misma lógica que los scripts de macOS/Linux
   (`uv run cafenorte <comando>`).

En Windows, `.env` se protege con permisos del usuario actual (`icacls`) en lugar de `600`, y
ShellCheck no aplica.

## Windows 10/11 con WSL2

Alternativa si prefieres un entorno Linux:

```powershell
# En PowerShell como administrador; reinicia al terminar
wsl --install -d Ubuntu
```

1. En Docker Desktop: *Settings → Resources → WSL integration*, activa **Ubuntu**.
2. Abre la terminal de Ubuntu y sigue la sección [Ubuntu / Debian](#ubuntu--debian) **sin
   instalar Docker** (lo aporta Docker Desktop).

> Clona el repositorio dentro del sistema de archivos de Linux (por ejemplo `~/proyectos`),
> no en `/mnt/c/...`: ahí los permisos `600` de `.env` no se aplican, los finales de línea pueden
> cambiar y Docker es mucho más lento. `doctor` lo detecta y te avisa.

## Ubuntu / Debian

```bash
# 1. Paquetes base (ss viene en iproute2)
sudo apt update
sudo apt install -y git curl shellcheck iproute2 ca-certificates

# 2. Docker Engine + Compose v2 (guía oficial: https://docs.docker.com/engine/install/ubuntu/)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"   # cierra sesión y vuelve a entrar
docker compose version

# 3. uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
```

## Fedora / RHEL / Rocky / Alma

```bash
# 1. Paquetes base
sudo dnf install -y git curl ShellCheck iproute

# 2. Docker Engine + Compose v2 (guía oficial: https://docs.docker.com/engine/install/fedora/)
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager addrepo --from-repofile=https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"   # cierra sesión y vuelve a entrar
docker compose version

# 3. uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
```

En RHEL, Rocky o Alma usa `https://download.docker.com/linux/centos/docker-ce.repo`; con dnf
anterior a la versión 5 el comando es `sudo dnf config-manager --add-repo <url>`. ShellCheck
requiere EPEL. Podman no está soportado: los scripts usan `docker compose`.

## Instalación (todas las plataformas)

```bash
git clone https://github.com/betoalien/CafeNorte-Tuxpas.git
cd CafeNorte-Tuxpas
uv sync
./scripts/start.sh      # Windows: scripts\windows\start.bat
./scripts/validate.sh   # Windows: scripts\windows\validate.bat
```

La primera vez, `start` genera `.env` con un puerto libre aleatorio para PostgreSQL y otro para
Superset, y contraseñas aleatorias. Las corridas siguientes reutilizan la misma configuración.
`.env` nunca se sube al repositorio.

## Qué esperar al arrancar

1. `doctor` revisa el entorno.
2. Se levantan PostgreSQL, Redis y Superset en Docker.
3. Se cargan las fuentes (con verificación de sus huellas SHA-256), se construyen las capas con
   dbt y se exportan las respuestas.
4. Aparece el bloque **Superset listo** con la liga directa al dashboard, los usuarios y la ruta
   del reporte.
5. Se abre en tu navegador el reporte HTML de la corrida (`artifacts/reports/run_report.html`):
   estado de cada fuente, conteos por capa, resultado de la validación, las cuatro respuestas y
   el acceso a Superset. Usa `--no-browser` si no quieres que se abra.

La primera corrida tarda alrededor de un minuto (más si Docker descarga imágenes). `validate`
corre las huellas de los originales, ShellCheck, la configuración de Docker, dbt, pytest, la
prueba de seguridad por tienda en Superset, la paridad de PardoX y Ruff.

## Ver los dashboards

| Usuario | Qué ve |
|---|---|
| `director` | Toda la red: las 40 tiendas y el canal en línea |
| `gerente_t001` | Solo la tienda T001 en quiebres, crecimiento por tienda y margen; la rotación es un indicador de red y la ve completa |
| `admin` | Solo administración de Superset |

Las contraseñas se generan para tu instalación. Para verlas:

```bash
./scripts/credentials.sh            # Windows: scripts\windows\credentials.bat
./scripts/start.sh --show-credentials
```

En el reporte HTML están ocultas detrás de un botón **Mostrar**. Si vas a compartir pantalla,
usa el reporte o `credentials` en una terminal que no estés compartiendo.

## Comandos disponibles

| macOS / Linux | Windows | Qué hace |
|---|---|---|
| `./scripts/start.sh` | `start.bat` | Levanta todo, carga lo que cambió y construye las respuestas |
| `./scripts/stop.sh` | `stop.bat` | Detiene PostgreSQL, Redis y Superset |
| `./scripts/restart.sh` | `restart.bat` | Detiene y vuelve a levantar con la misma configuración |
| `./scripts/status.sh` | `status.bat` | Estado de servicios, última corrida, conteos por capa y último dbt |
| `./scripts/validate.sh` | `validate.bat` | Todas las validaciones |
| `./scripts/credentials.sh` | `credentials.bat` | URL y contraseñas de esta instalación |
| `./scripts/doctor.sh` | `doctor.bat` | Diagnóstico del entorno |
| `./scripts/reset.sh --yes` | `reset.bat --yes` | Borra contenedores y volúmenes; nunca toca `datos/`, el código ni la documentación. Sin `--yes` no hace nada |

Los mismos comandos existen como `uv run cafenorte <comando>` en cualquier sistema.

## Cuando llegan datos nuevos

`start` compara la huella de cada archivo con la última corrida exitosa:

- **Sin cambios:** no toca nada y no reconstruye dbt (unos segundos).
- **Solo filas nuevas:** inserta únicamente esas; las existentes conservan su `run_id` original.
- **Una fila cambió o desapareció:** recarga completa de esa fuente; las demás no se tocan.

Para probarlo sin tocar los originales, apunta a una copia con la variable `CAFENORTE_DATA_DIR`.
Los archivos de `datos/` son del cliente y nunca se modifican; `validate` falla si su huella no
coincide con `datos/SHA256SUMS`.

## Plataformas probadas

| Plataforma | Estado |
|---|---|
| macOS arm64 (Apple Silicon) | Flujo completo validado a mano; PardoX probado |
| Ubuntu x86-64 | Flujo completo en GitHub Actions en cada push |
| Windows con WSL2 | Equivale a Ubuntu x86-64 |
| Windows nativo | Soportado; en CI se validan la CLI y `doctor` (GitHub no ejecuta contenedores Linux en Windows) |
| macOS Intel | Soportado; el binario de PardoX está incluido pero no verificado en CI |
| Linux ARM64 | Pipeline principal soportado; PardoX no tiene binario y se reporta como no disponible |

## Problemas comunes

| Síntoma | Solución |
|---|---|
| `Cannot connect to the Docker daemon` | Abre Docker Desktop, o en Linux `sudo systemctl start docker`; si es un permiso, `sudo usermod -aG docker $USER` y vuelve a iniciar sesión |
| `permission denied: ./scripts/start.sh` | `chmod +x scripts/*.sh` |
| `$'\r': command not found` | El repositorio se clonó con finales de línea de Windows; clónalo de nuevo dentro de WSL |
| `shellcheck is required` | macOS: `brew install shellcheck`; Ubuntu: `sudo apt install shellcheck`; Fedora: `sudo dnf install ShellCheck` |
| `fuente original del cliente modificada` | Algún archivo de `datos/` cambió; restaura los originales del cliente |
| `PardoX: UNSUPPORTED_PLATFORM` | Tu plataforma no tiene binario de PardoX; el resto de la validación sigue normal |
| El dashboard no carga | `./scripts/status.sh` muestra la URL y el puerto reales; usa esa liga |
