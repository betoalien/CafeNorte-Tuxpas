# Migración a macOS — archivo temporal (BORRAR del repo al terminar)

## 1. Contexto para la nueva sesión de Claude en la Mac

La memoria de Claude Code es local a la máquina Windows; **no viaja con el repo**. Al abrir Claude Code en la Mac, la primera instrucción debe ser: *"Lee MIGRATION-MACOS-DELETEME.MD, AGENTS.md, AI_LOG.md y docs/ antes de cualquier cosa"*.

### Forma de trabajo (acordada)
- **Codex** hace el trabajo pesado (código, docs, pruebas).
- **Claude Code** revisa con dureza, verifica contra los datos y redacta los prompts para Codex.
- **Alberto** decide. Las decisiones tomadas no se vuelven a debatir.

### Perfil del propietario
7 años como data analyst y 3 como data engineer: perfil híbrido (pipeline desde cero + dashboard final). Autor de PardoX (www.pardox.io), motor DataFrame en Rust ubicado entre Polars y Spark; en este reto es solo una demostración, nunca parte del camino crítico.

### Decisiones cerradas (no reabrir)
- Solo **PostgreSQL** (DuckDB descartado). Polars es la referencia; PardoX, una alternativa con paridad.
- **dbt** es dueño de la semántica. **Pydantic** valida contratos y manifests.
- Scripts del harness con los nombres actuales: `start`, `stop`, `restart`, `reset --yes`, `validate`, `status`.
- Visor: **Apache Superset** (ADR-006). Local: `psycopg2` contra `analytics`, Redis, RLS por tienda. AWS: PyAthena, OAuth, HTTPS. Tableau es un bonus opcional.
- AWS: todo en `us-east-1` con Superset en Lightsail; total ~USD 34.49/mes y USD 165.51 de margen. Alternativa México: todo en `mx-central-1` con EC2.
- Datos sintéticos: se publican, pero la PII igual se excluye de Silver y Gold.
- `tipo_comprobante` es un atributo del CFDI: **se cuenta, nunca se suma ni se resta**. Todas las filas son ventas.
- `monto` es importe neto sin IVA (supuesto documentado).
- Maestro de tiendas = ERP `tiendas_info`. La discrepancia con lo que dijo el cliente se reporta.
- FX: tasa del día; EUR = 22.0 se marca con `fx_quality_flag` y se usa.
- P2: se lista la tienda si algún SKU tuvo más de 3 días seguidos con stock = 0; N/A rompe la secuencia.
- P4: POS por tienda; e-commerce como canal `ONLINE`.
- Ventanas ancladas en 2026-03-31.
- Puerto de PostgreSQL aleatorio (demo en Mac y algo de seguridad por no usar el puerto por defecto).

## 2. Estado actual

| Bloque | Estado |
|---|---|
| Especificación, propuesta AWS, ADR 001–006 | Aprobado |
| A: perfilado + harness + PostgreSQL | Aprobado |
| A-1: correcciones y decisiones | **Aprobado con un hallazgo crítico pendiente (ver 3)** |
| B: Pydantic + Polars → Silver + cuarentena | Pendiente |
| C: dbt → Gold + 4 respuestas | Pendiente |
| D: Superset + RLS, PardoX con paridad, README final | Pendiente |

## 3. Revisión del Bloque A-1 (Claude)

### Crítico: la cobertura del 100% está mal contada
`sku_mappings` contiene **5 mappings con `sku_erp = null`**: CN-00006, 016, 026, 036 y 046. `profile_sources.py` (líneas ~382-403) los cuenta como `explicit` porque solo comprueba si existe la clave, no si `sku_erp` tiene valor.
- POS afectado: **6,132 filas y 2,524,147.68 MXN** marcadas como "explicit" que en realidad apuntan a null.
- Shopify afectado: 1,139 filas (handles -006, -026, -036, -046).
- Si esto pasa a Silver, el join con costo e inventario devuelve null y P1 y P4 salen mal sin dar error.
- Corrección: un mapping explícito vale solo si `sku_erp` no es null; si es null, se aplica el respaldo por número. Hay que medir de nuevo y reportar tres métodos: `explicit`, `product_number` (sin fila de mapping) y `product_number_null_erp` (con fila pero ERP nulo).
- Verificado: no hay mappings explícitos que contradigan el número de producto ni `sku_pos` duplicados. El patrón de trampas es que cada familia de terminación (1 y 6) rompe el mapping de forma distinta.

### Menores
1. `.env.example` dice "start.sh resolves auto once", pero `start.sh` **rechaza** `POSTGRES_PORT=auto`. Hay que alinear el comentario: el `.env` se genera solo cuando no existe; el ejemplo es documentación.
2. `start.sh` usa Python para el puerto aleatorio. En una Mac limpia, `python3` puede abrir la ventana de instalación de Xcode CLT a mitad de la demo. Mejor usar bash puro: `$(( 20000 + (RANDOM * 32768 + RANDOM) % 40001 ))`, con `lsof` para comprobar que esté libre.
3. `validate.sh` ejecuta `profile_sources.py`, que reescribe `profiling.md` con un timestamp nuevo en cada corrida y ensucia el diff de git. Separar el perfilado (`uv run python scripts/profile_sources.py` manual) de la validación, o escribir la salida a un archivo temporal y comparar.
4. ShellCheck: instalarlo en la Mac (`brew install shellcheck`) y correrlo de verdad.

## 4. Preparar la Mac

```bash
# Requisitos
xcode-select --install            # Git y CLT (si no están)
brew install uv shellcheck openssl
# Docker Desktop para Apple Silicon: https://www.docker.com/products/docker-desktop/

# Repo
git clone <url-del-repo> && cd <repo>        # o git pull si ya existe
uv sync
chmod +x scripts/*.sh

# Archivos que NO están en el repo (ignorados): copiarlos a mano si se quieren tener localmente
#   TX Challenge Data Solutions Engineer.pdf / .docx, datos_cafenorte*.zip
# .env NO se copia: start.sh genera uno nuevo con puerto y contraseñas aleatorios.

# Prueba de humo
./scripts/start.sh      # genera .env y levanta PostgreSQL en el puerto aleatorio
./scripts/status.sh
./scripts/validate.sh
./scripts/restart.sh    # el puerto y las credenciales deben seguir iguales
./scripts/reset.sh      # sin --yes no debe borrar nada
```

Verificar en la Mac:
- `bash --version` es 3.2: los scripts no deben fallar.
- La imagen `postgres:16.4-alpine3.20` corre nativa en arm64.
- `stat -f %Lp .env` devuelve `600`.
- `shasum -a 256 datos/*` no cambia después de `reset.sh --yes`.

## 5. Prompt para Codex: Bloque A-2 (corrección antes de B)

```text
Bloque A-2. Solo correcciones; detente al terminar.
1. profile_sources.py: un mapping explícito solo cuenta si sku_erp no es null. Los 5 mappings con sku_erp=null (CN-00006/016/026/036/046 y sus handles) usan el respaldo por número. Reporta tres métodos (explicit, product_number, product_number_null_erp) con filas, unidades y monto, y valida que el número recuperado exista en el catálogo.
2. Agrega a profiling.md una sección "Mappings con sku_erp nulo" con la lista y su impacto (POS: 6,132 filas / 2,524,147.68 MXN; Shopify: 1,139 filas).
3. DATA_CONTRACTS y BUSINESS_METRICS: la regla de conciliación trata sku_erp nulo como ausencia de mapping.
4. start.sh: puerto aleatorio en bash puro, sin Python; comprobación con lsof en macOS.
5. .env.example: corrige el comentario de POSTGRES_PORT=auto.
6. validate.sh: no regenera profiling.md; el perfilado queda como comando aparte documentado en RUNBOOK.
7. Corre shellcheck (ya instalado) y corrige los avisos.
8. AI_LOG: caso de error. Codex reportó 100% de cobertura contando como "explicit" mappings con sku_erp nulo; Claude lo detectó verificando contra inventory.json. Lección: "existe la clave" no es "el valor es válido".
9. Evidencia en artifacts/evidence/block-a2-validation.md, ejecutada en macOS.
```

## 6. Después de A-2

Pedirle a Claude en la Mac: *"Revisa el Bloque A-2 y arma el prompt del Bloque B"*. Requisitos del Bloque B que ya están decididos:
- Contratos Pydantic por fuente.
- Polars → `silver` en PostgreSQL con carga idempotente (`run_id`).
- `stock_quantity` nullable más `stock_raw_value` / `quality_status` para los N/A.
- Columnas `match_method` y `fx_quality_flag`.
- PII fuera de Silver.
- Cuarentena en `audit` con su motivo.
- Pruebas pytest de las reglas críticas: N/A ≠ 0, PII ausente, mapping nulo → respaldo, CFDI no altera el signo, idempotencia.

## 7. Al terminar la migración
Este archivo viaja a la Mac con el repo (commit + pull). En cuanto la Mac esté operativa: `git rm MIGRATION-MACOS-DELETEME.MD` y commit, para que no llegue a la entrega final.
