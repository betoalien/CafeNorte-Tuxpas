# CaféNorte Data Platform Challenge

[![CI](https://github.com/betoalien/CafeNorte-Tuxpas/actions/workflows/ci.yml/badge.svg)](https://github.com/betoalien/CafeNorte-Tuxpas/actions/workflows/ci.yml)

## Qué Resuelve

- **P1:** los tres primeros son `057-C` (1.362), `012-B` (1.226) y `041-D` (1.201) en rotación de red.
- **P2:** las tiendas con rachas certificadas son `T015`, `T023` y `T038`.
- **P3:** muestra la tendencia mensual de `ONLINE` frente a cada tienda POS, en MXN.
- **P4:** tres productos tienen margen negativo en las 40 tiendas en los últimos 12 meses: `015-D` (−158,216 MXN), `002-B` (−47,596) y `001-A` (−12,664). Con todo el histórico POS (desde 2024-10) son los mismos tres; 015-D llega a −230,810. ONLINE no tiene margen negativo.

Las respuestas completas y sus periodos están en [`artifacts/evidence/answers/`](artifacts/evidence/answers/).

## Arquitectura

```text
datos/ (solo lectura) -> contratos + cuarentena -> Polars -> PostgreSQL Silver
                                             -> dbt -> analytics Gold -> Superset/RLS
                                             -> audit/manifests/evidencia
                                      PardoX: ruta alternativa aislada para sales.csv
```

Polars es la referencia reproducible; Pydantic hace explícitos los contratos; PostgreSQL aporta
transacciones, trazabilidad y serving; dbt posee conciliación, FX, costos y métricas; Superset solo
consulta Gold. Redis se limita a caché de Superset. PardoX demuestra una alternativa de motor sin
convertirse en dependencia del camino crítico.

## Estado

Bloques A, A-1, B, C y D1 implementados. D2 queda entregado como ruta experimental documentada;
PardoX no reemplaza Silver cuando falla una guarda de paridad.

## Ver los dashboards

Después de `./scripts/start.sh`, abre `http://127.0.0.1:<SUPERSET_PORT>` usando el puerto que
reporta `./scripts/status.sh`. El dashboard es **CaféNorte — 4 respuestas**. Los usuarios demo son
`admin`, `director` y `gerente_t001`; sus contraseñas se generan al crear `.env` y permanecen solo
en `.env` (permisos 600). `gerente_t001` solo ve T001 en P2/P3/P4; `director` ve toda la red sin
ser `Admin`; P1 es un indicador de red y lo ven todos los roles.

## Datos Nuevos

`skipped` conserva Silver y no ejecuta dbt ni exporta; `incremental` inserta solo claves nuevas;
`full` reemplaza la tabla de la fuente cuando cambia una fila o desaparece una clave. Los maestros
pequeños usan `full`. Para probar copias, usa `CAFENORTE_DATA_DIR`; `datos/` nunca se modifica.

## Calidad y Supuestos

- Los cinco mappings con `sku_erp` nulo se conservan y se concilian por número de producto cuando procede.
- Los cuatro archivos originales del cliente son inmutables. Verifica sus hashes desde la raíz con
  `cd datos && shasum -a 256 -c SHA256SUMS` en macOS o `sha256sum -c SHA256SUMS` en Linux; `validate.sh`
  ejecuta esta guarda y falla si aparece `fuente original del cliente modificada`.
- CFDI no cambia signo ni inclusión; las 86,490 filas se cuentan por tipo.
- `N/A` significa desconocido, nunca cero; EUR 22.0 se conserva con bandera de calidad.
- `tiendas_info` es el maestro y sus tiendas/regiones fuera del relato se reportan, no se corrigen silenciosamente.
- Shopify contiene PII que se excluye de Silver y Gold; la hora POS se trata como hora local de tienda y dbt puede usar la zona del maestro.
- Se supone que `monto` es neto sin IVA y que las fechas de las fuentes son comparables para el ancla común.
- En plataformas sin binario PardoX, `validate.sh` reporta `PardoX: UNSUPPORTED_PLATFORM (<os>-<arch>)`,
  omite solo sus pruebas y conserva la validación del pipeline Polars. En plataformas soportadas,
  la paridad PardoX sigue siendo obligatoria.

**Costo AWS:** la propuesta estimada es **USD 34.49/mes** con contingencia; ver [`docs/PROPUESTA_AWS.md`](docs/PROPUESTA_AWS.md).

## Plataformas probadas

- macOS arm64: validación manual completa; PardoX soportado (probado). Usa el Python arm64 que instala uv.
- macOS x86_64: binario PardoX incluido en 0.3.4, no verificado por falta de runners Intel; si no carga,
  se reporta `UNSUPPORTED_PLATFORM` sin tumbar Polars.
- Ubuntu x86_64: validación continua en GitHub Actions.
- WSL2: Ubuntu x86_64, ejecutando el repositorio dentro del filesystem Linux.
- Linux ARM64: PardoX no disponible; Polars sigue siendo el pipeline principal.

En Apple Silicon, Python bajo Rosetta reporta `x86_64` y puede intentar cargar el binario Intel;
usa el Python arm64 instalado por uv.

## Capas

- **Bronze:** archivos originales y manifiestos; nunca se modifican.
- **Silver:** entidades técnicamente normalizadas y PII excluida.
- **Gold:** dimensiones, hechos, métricas y marts certificados por dbt.
- **Audit:** cuarentena, reconciliaciones, calidad y ejecuciones.

## PardoX

PardoX es un motor DataFrame con núcleo en Rust, publicado en [pardox.io](https://www.pardox.io/).
Por SPEC-003, solo `sales.csv` recorre PardoX de punta a punta; inventario, Shopify y FX quedan en
Polars. El bloque demuestra paridad, carga nativa y tiempos, no reemplaza la ingesta crítica.

Resultados: a ×1 PardoX `to_sql` totaliza 0.173562 s frente a 0.441900 s de Polars; a ×10,
1.964213 s frente a 2.664857 s. `write_sql_prdx` queda excluido a ×10 por fallo de paridad;
la [reproducción](artifacts/evidence/pardox-0.3.4-prdx-repro/README.md) documenta el caso.

### ¿Por qué existe PardoX?

PardoX nació de una brecha concreta: **pandas se queda sin memoria** con volúmenes grandes y
**Polars**, aunque robusto, vive dentro del ecosistema de dependencias de Python. Spark resuelve
la escala, pero solo habla Java/Scala y Python, y exige una JVM o un clúster.

- **Cero dependencias de lenguaje.** Toda la lógica vive en un núcleo Rust; Python, Node.js y PHP
  son bindings delgados. Leer CSV/Parquet, validar contratos, transformar y escribir a
  PostgreSQL no requiere psycopg2, SQLAlchemy ni pyarrow.
- **Universalidad.** Miles de tiendas en línea y sitios web corren en PHP (Laravel, Symfony) o
  Node.js y necesitan llevar sus datos a un dataset sin un clúster JVM. El paquete incluye
  binarios para macOS (ARM/Intel), Linux x86-64, Windows, Node (N-API) y WASM.
- **Hasta el mainframe.** En una prueba propia del autor, un programa COBOL llamó al núcleo de
  PardoX por FFI (DLL/.so) y convirtió un archivo `.dat` de mainframe con 50 millones de registros
  a `.prdx` en ~90 segundos, sin capas de traducción intermedias.
- **PostgreSQL sin intermediarios.** El protocolo binario de PostgreSQL está implementado en Rust:
  los datos van de la base a la memoria del motor (y de regreso, con `to_sql`) sin convertirse en
  objetos Python.
- **Motor propio, no un wrapper.** El núcleo no depende de Apache Arrow: usa estructuras propias en
  Rust y paralelismo con Rayon, con una heurística que decide qué porcentaje de CPU dedicar a cada
  lectura y escritura según la carga.
- **Formato `.prdx`.** Bloques comprimidos con Zstd pensados para escribir y recargar rápido
  (no para el menor tamaño: en este reto el parquet de Polars pesa menos).

**Qué demuestra en este reto:** paridad fila por fila con Polars sobre `sales.csv`, verificada en
PostgreSQL, y la carga a PostgreSQL más rápida de las tres rutas medidas. Polars gana en cómputo en
memoria a ×10. Polars sigue siendo el motor de referencia; PardoX es una alternativa verificada,
nunca el camino crítico. La guarda de paridad encontró un bug real en la ruta `.prdx` de la
versión 0.3.4 (offsets UTF-8 sin rebase entre bloques), documentado en la reproducción.

**Fuera de este reto:** en una prueba propia del autor (640 millones de filas en 320 CSV, laptop
Ryzen 5 con 16 GB), PardoX tardó 182 s contra 204 s de Polars, con 1.13 GB de RAM.

## Uso de IA y limitaciones

La bitácora de decisiones, errores y correcciones está en [`AI_LOG.md`](AI_LOG.md). Limitaciones
conocidas: PardoX es experimental para este volumen; `write_sql_prdx` falla la guarda x10; los
precios AWS son una estimación; la autenticación de Superset es local; y la zona horaria POS es un
supuesto de hora local que dbt puede convertir usando el maestro de tiendas.

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
