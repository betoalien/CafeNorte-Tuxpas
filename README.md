# CaféNorte Data Platform Challenge

## Estado

Bloques A, A-1, B y C implementados: perfilado, Bronze → Silver, dbt → Gold y las cuatro
respuestas reproducibles. PardoX, Redis y Superset permanecen pendientes.

## Objetivo

Crear una fuente analítica confiable para ventas e inventario de CaféNorte y responder:

1. Top 10 SKU por rotación de inventario en los últimos seis meses.
2. Tiendas con quiebres de stock mayores a tres días en el último trimestre.
3. Crecimiento mensual de ventas por canal durante el último año.
4. Productos con margen negativo y las tiendas donde ocurren.

## Arquitectura local decidida

```text
Fuentes inmutables
        |
Contratos Pydantic
        |
Polars (referencia) / PardoX (alternativa verificada)
        |
PostgreSQL Silver
        |
dbt: intermedia, dimensiones, hechos y marts
        |
PostgreSQL Gold
        |
Apache Superset
```

Polars y PardoX realizan la preparación columnar. PostgreSQL persiste y sirve los datos. dbt es propietario de las reglas de negocio y la capa semántica materializada. Superset consulta únicamente Gold mediante `psycopg2` y aplica RLS por tienda.

## Capas

- **Bronze:** archivos originales y manifiestos; nunca se modifican.
- **Silver:** entidades técnicamente normalizadas y PII excluida.
- **Gold:** dimensiones, hechos, métricas y marts certificados por dbt.
- **Audit:** cuarentena, reconciliaciones, calidad y ejecuciones.

## Documentación

- `docs/SYSTEM_MAP.md`: mapa conceptual.
- `docs/DATA_CONTRACTS.md`: contratos de fuentes y capas.
- `docs/BUSINESS_METRICS.md`: definiciones de métricas.
- `docs/IMPLEMENTATION_PLAN.md`: fases y gates.
- `docs/specs/`: especificaciones verificables.
- `docs/decisions/`: decisiones arquitectónicas.
- `docs/RUNBOOK.md`: contrato operativo.
- `AI_LOG.md`: bitácora obligatoria de uso de IA.

## Datos

La carpeta `datos/` contiene tres fuentes operacionales y un dataset auxiliar de tipos de cambio. Son datos sintéticos proporcionados para el reto y se publican como parte de este repositorio. Aunque no representan personas reales, el pipeline trata los campos de identificación como PII y los excluye de Silver y Gold.

## Requisitos

| Herramienta | Uso | Versión |
|---|---|---|
| Git | Clonar el repositorio | Cualquiera reciente |
| Docker + Docker Compose v2 | PostgreSQL (y después Superset) | Docker Engine 24+ / Docker Desktop |
| uv | Entorno Python reproducible (`uv.lock`) | 0.4+ (instala Python 3.12 por sí mismo) |
| OpenSSL | Genera las contraseñas aleatorias de `.env` | Cualquiera |
| Bash | Scripts del harness | 3.2+ (compatible con el Bash de macOS) |
| ShellCheck | Validación de scripts (`validate.sh`) | Cualquiera reciente |

No hace falta instalar Python a mano: `uv sync` descarga Python 3.12 si no está presente.

### macOS (Intel o Apple Silicon)

```bash
# 1. Herramientas de línea de comandos (incluye Git)
xcode-select --install

# 2. Homebrew (si no lo tienes): https://brew.sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 3. Dependencias
brew install uv shellcheck openssl

# 4. Docker Desktop (elige la versión Apple Silicon o Intel)
#    https://www.docker.com/products/docker-desktop/
#    Ábrelo una vez y espera a que diga "Engine running".
docker compose version
```

`lsof`, que usa `start.sh` para comprobar que el puerto esté libre, ya viene con macOS.

### Windows 10/11 (mediante WSL2)

Los scripts son Bash, así que en Windows se ejecutan dentro de WSL2 con Ubuntu.

```powershell
# 1. En PowerShell como administrador: instala WSL2 con Ubuntu y reinicia
wsl --install -d Ubuntu
```

2. Instala [Docker Desktop para Windows](https://www.docker.com/products/docker-desktop/) y en
   *Settings → Resources → WSL integration* activa la integración con **Ubuntu**.
3. Abre la terminal de **Ubuntu** y sigue la sección [Ubuntu / Debian](#ubuntu--debian),
   **omitiendo la instalación de Docker** (ya lo aporta Docker Desktop).

> Importante: clona el repositorio dentro del sistema de archivos de Linux (por ejemplo
> `~/proyectos`), no en `/mnt/c/...`. En `/mnt/c` los permisos `600` de `.env` no se aplican,
> los finales de línea pueden cambiar y Docker es mucho más lento.

### Ubuntu / Debian

```bash
# 1. Paquetes base (ss viene en iproute2)
sudo apt update
sudo apt install -y git curl openssl shellcheck iproute2 ca-certificates

# 2. Docker Engine + Compose v2 (repositorio oficial de Docker)
#    Guía: https://docs.docker.com/engine/install/ubuntu/
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"   # cierra sesión y vuelve a entrar
docker compose version

# 3. uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
```

### Fedora / RHEL / Rocky / Alma

```bash
# 1. Paquetes base
sudo dnf install -y git curl openssl ShellCheck iproute

# 2. Docker Engine + Compose v2 (repositorio oficial de Docker)
#    Guía: https://docs.docker.com/engine/install/fedora/
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

En RHEL, Rocky o Alma usa `https://download.docker.com/linux/centos/docker-ce.repo`, y en
versiones de dnf anteriores a la 5 el comando es
`sudo dnf config-manager --add-repo <url>`. ShellCheck requiere tener EPEL habilitado.
Si usas Podman en lugar de Docker, no está soportado: los scripts llaman a `docker compose`.

## Instalación (todas las plataformas)

```bash
git clone https://github.com/betoalien/CafeNorte-Tuxpas.git
cd CafeNorte-Tuxpas
uv sync                 # crea .venv con Python 3.12 y las dependencias fijadas
chmod +x scripts/*.sh
```

`.env` **no** se copia ni se versiona: el primer `start.sh` lo genera con un puerto libre
aleatorio (20000–60000), contraseñas aleatorias y permisos `600`. Los reinicios reutilizan esa
misma configuración.

## Ejecución

```bash
./scripts/start.sh      # genera .env, Bronze → Silver, dbt build y exporta respuestas
./scripts/status.sh     # estado, último run_id y conteos Silver/Gold
./scripts/validate.sh   # ShellCheck, pytest, dbt build/test, Ruff y controles PostgreSQL
./scripts/restart.sh    # reinicia conservando puerto y credenciales
./scripts/stop.sh       # detiene los servicios
./scripts/reset.sh      # sin --yes solo muestra lo que borraría
./scripts/reset.sh --yes  # borra volúmenes y estado local; nunca toca datos/, docs ni AI_LOG.md
```

### Verificación rápida

```bash
docker compose version                     # Compose v2
grep POSTGRES_PORT .env                    # puerto asignado
stat -f %Lp .env 2>/dev/null || stat -c %a .env   # debe imprimir 600 (macOS || Linux)
shasum -a 256 datos/* 2>/dev/null || sha256sum datos/*   # los hashes no cambian tras reset
```

### Problemas comunes

- **`Cannot connect to the Docker daemon`**: Docker Desktop no está abierto, o en Linux el
  servicio no está activo (`sudo systemctl start docker`) o tu usuario aún no está en el grupo
  `docker` (cierra sesión y vuelve a entrar).
- **`permission denied: ./scripts/start.sh`**: ejecuta `chmod +x scripts/*.sh`.
- **`$'\r': command not found`**: el repositorio se clonó con finales de línea de Windows.
  Clónalo de nuevo dentro de WSL; `.gitattributes` fuerza `LF` para los scripts.
- **`.env contains POSTGRES_PORT=auto`**: borra `.env` y vuelve a ejecutar `start.sh`.

## Interpretaciones

Estas reglas fueron cerradas por el propietario a partir de la
[evidencia de perfilado](artifacts/evidence/profiling.md#interpretaciones-cerradas-por-el-propietario):

1. `tipo_comprobante` es un atributo del CFDI. Todas las filas son ventas; el CFDI se cuenta por
   tipo y nunca hace que monto o cantidad se sumen, resten o excluyan de forma distinta.
2. Silver solo expone las columnas técnicas. La conciliación se resuelve en dbt: mapping explícito
   primero solo cuando `sku_erp` no es nulo, y número de producto con nombre validado como respaldo.
   `sku_erp = null` equivale a ausencia de mapping explícito y puede producir
   `product_number_null_erp`; `match_method` será `explicit`, `product_number` o
   `product_number_null_erp`; lo no conciliado va a Audit.
3. `monto` se supone neto sin IVA: no hay campo de impuesto y las categorías tienen tasas 0%/16%.
4. `tiendas_info` del ERP es el maestro. Sus diferencias contra el relato del cliente se reportan.
5. FX usa la tasa del día. EUR=22.0 se usa con `fx_quality_flag` por posible truncamiento.
6. P2 lista una tienda si algún SKU tuvo más de tres días consecutivos con stock cero; `N/A`
   rompe la secuencia. Se conserva SKU, inicio, fin y días.
7. P4 reporta POS por tienda y e-commerce como canal `ONLINE`.
8. Las ventanas se anclan en 2026-03-31. Inventario cubre exactamente seis meses y el MoM de
   e-commerce de 2025-04 queda `null` por falta de base.
9. Gold incluirá un mart de reconciliación que explique diferencias entre POS, ERP y Shopify.
