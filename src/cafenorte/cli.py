"""Cross-platform orchestration CLI for the CaféNorte local stack."""

from __future__ import annotations

import argparse
import json
import os
import platform
import secrets
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
INIT_SCRIPT = ROOT / "docker/postgres/init/001_initialize.sh"

ANCHOR_DATE_SQL = (
    'SELECT LEAST((SELECT max(fecha_hora_normalizada::date) FROM silver.pos_sales), '
    '(SELECT max(fecha::date) FROM silver.ecommerce_orders), '
    '(SELECT max(fecha) FROM silver.inventory_snapshots));'
)
LAST_RUN_SQL = (
    "SELECT run_id, status, input_count, accepted_count, rejected_count "
    "FROM audit.run_log ORDER BY started_at DESC LIMIT 1;"
)
SILVER_COUNTS_SQL = (
    "SELECT table_name, row_count FROM ("
    "SELECT 'silver.pos_sales' AS table_name, count(*) AS row_count FROM silver.pos_sales "
    "UNION ALL SELECT 'silver.inventory_snapshots', count(*) FROM silver.inventory_snapshots "
    "UNION ALL SELECT 'silver.ecommerce_orders', count(*) FROM silver.ecommerce_orders "
    "UNION ALL SELECT 'silver.exchange_rates', count(*) FROM silver.exchange_rates "
    "UNION ALL SELECT 'silver.stores', count(*) FROM silver.stores "
    "UNION ALL SELECT 'silver.products', count(*) FROM silver.products "
    "UNION ALL SELECT 'silver.sku_mappings', count(*) FROM silver.sku_mappings"
    ") counts ORDER BY table_name;"
)
GOLD_COUNTS_SQL = (
    "SELECT table_name, row_count FROM ("
    "SELECT 'analytics.mart_inventory_turnover_top10' AS table_name, count(*) AS row_count "
    "FROM analytics.mart_inventory_turnover_top10 "
    "UNION ALL SELECT 'analytics.mart_stockouts_over_3_days', count(*) "
    "FROM analytics.mart_stockouts_over_3_days "
    "UNION ALL SELECT 'analytics.mart_monthly_channel_growth', count(*) "
    "FROM analytics.mart_monthly_channel_growth "
    "UNION ALL SELECT 'analytics.mart_negative_margin_products', count(*) "
    "FROM analytics.mart_negative_margin_products "
    "UNION ALL SELECT 'analytics.mart_source_reconciliation', count(*) "
    "FROM analytics.mart_source_reconciliation"
    ") gold_counts ORDER BY table_name;"
)
SCHEMAS_ROLES_SQL = (
    "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN "
    "('silver', 'audit', 'intermediate', 'analytics'); "
    "SELECT rolname FROM pg_roles WHERE rolname IN "
    "('pipeline', 'dbt', 'superset_ro', 'superset_meta'); "
    "SELECT datname FROM pg_database WHERE datname = 'superset_meta';"
)


def psql_command(sql: str, *, readonly: bool = False) -> str:
    stop = ' --set=ON_ERROR_STOP=1' if not readonly else ""
    output = " -At" if readonly else ""
    return (
        'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"'
        f"{stop}{output} -c \"{sql}\""
    )

STEP_PLANS = {
    "start": [
        "doctor",
        "env",
        "compose postgres redis",
        "postgres healthy",
        "ingest",
        "anchor_date",
        "dbt build",
        "export answers",
        "superset healthy",
        "status",
        "report",
    ],
    "restart": ["stop", "start"],
    "stop": ["compose stop"],
    "status": [
        "pg_isready",
        "run_log",
        "silver counts",
        "dbt result",
        "gold counts",
        "report path",
    ],
    "validate": [
        "doctor",
        "source checksums",
        "bash -n",
        "shellcheck",
        "compose config",
        "schemas roles superset_meta",
        "anchor_date",
        "pardox force",
        "dbt build",
        "pytest",
        "superset RLS",
        "ruff",
        "export answers",
    ],
    "reset": ["compose down volumes"],
    "credentials": ["read .env", "print credentials"],
    "doctor": [
        "platform",
        "docker",
        "compose v2",
        "uv",
        "shellcheck",
        "port tool",
        "pardox platform",
    ],
}


def step_plan(command: str) -> list[str]:
    return list(STEP_PLANS[command])


def load_env(path: Path | None = None) -> dict[str, str]:
    path = path or ENV_PATH
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"').strip("'")
    return values


def run(
    command: list[str], *, check: bool = True, capture: bool = False, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd or ROOT,
        check=check,
        text=True,
        capture_output=capture,
        env=os.environ.copy(),
    )


def report_ingest_failure(stderr: str) -> None:
    """Show bounded ingestion diagnostics without guessing at unrelated failures."""
    detail = stderr.splitlines()[-20:]
    if detail:
        print("Detalle de la ingesta:", file=sys.stderr)
        print("\n".join(detail), file=sys.stderr)
    if "password authentication failed" in stderr:
        print(
            "ERROR: la ingesta falló por credenciales antiguas; ejecuta "
            "`uv run cafenorte reset --yes` y vuelve a iniciar.",
            file=sys.stderr,
        )
    else:
        print("ERROR: la ingesta falló; revisa el detalle arriba", file=sys.stderr)


def compose(
    env: dict[str, str], *args: str, check: bool = True, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    return run(
        ["docker", "compose", "--env-file", str(ENV_PATH), *args], check=check, capture=capture
    )


def compose_exec(
    env: dict[str, str], command: str, *, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    return compose(env, "exec", "-T", "postgres", "sh", "-c", command, capture=capture)


def sync_database_roles(env: dict[str, str]) -> None:
    """Reuse the role ALTER statements from the PostgreSQL init script."""
    statements = [
        line.strip()
        for line in INIT_SCRIPT.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("ALTER ROLE") and "PASSWORD" in line
    ]
    statements.insert(0, "ALTER ROLE cafenorte_admin PASSWORD :'admin_password';")
    sql = "\\set admin_password '" + env["POSTGRES_PASSWORD"] + "'\n"
    variables = {
        "pipeline_password": env["PIPELINE_PASSWORD"],
        "dbt_password": env["DBT_PASSWORD"],
        "superset_ro_password": env["SUPERSET_RO_PASSWORD"],
        "superset_meta_password": env["SUPERSET_META_PASSWORD"],
    }
    for name, value in variables.items():
        sql += f"\\set {name} '{value}'\n"
    sql += "\n".join(statements) + "\n"
    result = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "cafenorte-postgres",
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            env["POSTGRES_USER"],
            "-d",
            env["POSTGRES_DB"],
        ],
        input=sql,
        text=True,
        capture_output=True,
        env=os.environ.copy(),
    )
    if result.returncode:
        print(
            "AVISO: no se pudieron sincronizar las contraseñas de PostgreSQL; "
            "se continúa con el flujo normal.",
            file=sys.stderr,
        )


def free_port() -> int:
    for _ in range(100):
        candidate = 20000 + secrets.randbelow(40001)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", candidate))
            except OSError:
                continue
            return candidate
    raise RuntimeError("No se encontró un puerto libre entre 20000 y 60000.")


def write_env() -> dict[str, str]:
    if ENV_PATH.exists():
        return load_env()
    values = {
        "POSTGRES_DB": "cafenorte",
        "POSTGRES_USER": "cafenorte_admin",
        "POSTGRES_PASSWORD": secrets.token_hex(24),
        "PIPELINE_PASSWORD": secrets.token_hex(24),
        "DBT_PASSWORD": secrets.token_hex(24),
        "SUPERSET_RO_PASSWORD": secrets.token_hex(24),
        "SUPERSET_META_PASSWORD": secrets.token_hex(24),
        "SUPERSET_SECRET_KEY": secrets.token_hex(32),
        "SUPERSET_ADMIN_PASSWORD": secrets.token_hex(24),
        "GERENTE_T001_PASSWORD": secrets.token_hex(24),
        "DIRECTOR_PASSWORD": secrets.token_hex(24),
        "POSTGRES_PORT": str(free_port()),
        "SUPERSET_PORT": str(free_port()),
    }
    ENV_PATH.write_text(
        "".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8"
    )
    secure_env()
    print(f"Generated .env with PostgreSQL port {values['POSTGRES_PORT']}.")
    return values


def secure_env() -> None:
    if os.name == "nt":
        username = os.environ.get("USERNAME", "")
        if username:
            run(
                ["icacls", str(ENV_PATH), "/inheritance:r", "/grant:r", f"{username}:F"],
                check=False,
            )
    else:
        ENV_PATH.chmod(0o600)


def doctor() -> int:
    system, machine = platform.system(), platform.machine()
    wsl = (
        system == "Linux"
        and "microsoft" in Path("/proc/version").read_text(errors="ignore").lower()
        if Path("/proc/version").exists()
        else False
    )
    print(f"Doctor: OS={system} arch={machine}{' WSL' if wsl else ''}")
    failed = False
    for command, fix in [
        ("docker", "instala Docker Desktop o Docker Engine"),
        ("uv", "instala uv desde https://docs.astral.sh/uv/"),
    ]:
        if shutil.which(command) is None:
            print(f"ERROR: {command} no está instalado. Arreglo: {fix}", file=sys.stderr)
            failed = True
    if shutil.which("docker"):
        if run(["docker", "info"], check=False, capture=True).returncode:
            print(
                (
                    "ERROR: el daemon de Docker no es accesible. En Linux: "
                    "sudo usermod -aG docker $USER o sudo systemctl start docker."
                ),
                file=sys.stderr,
            )
            failed = True
        if run(["docker", "compose", "version"], check=False, capture=True).returncode:
            print("ERROR: se requiere Docker Compose v2.", file=sys.stderr)
            failed = True
        else:
            print("OK: Docker Compose v2")
    if system != "Windows" and shutil.which("shellcheck") is None:
        print("ERROR: shellcheck no está instalado.", file=sys.stderr)
        failed = True
    if system == "Darwin" and shutil.which("lsof") is None:
        print("ERROR: instala lsof.", file=sys.stderr)
        failed = True
    if system == "Linux" and not (shutil.which("ss") or shutil.which("netstat")):
        print("ERROR: instala ss (iproute2) o netstat.", file=sys.stderr)
        failed = True
    if wsl and str(ROOT).startswith("/mnt/"):
        print(
            "ERROR: WSL debe usar el filesystem Linux, no /mnt/; clona de nuevo dentro de WSL.",
            file=sys.stderr,
        )
        failed = True
    if any("\r" in path.read_text(errors="ignore") for path in (ROOT / "scripts").glob("*.sh")):
        print("AVISO: hay CRLF en scripts/*.sh; clona de nuevo dentro de WSL.", file=sys.stderr)
    if system == "Darwin" and machine == "arm64":
        print("PardoX: soportado (probado)")
    elif system == "Darwin" and machine == "x86_64":
        print("PardoX: binario incluido en 0.3.4, no verificado (sin runners macOS Intel en CI)")
    elif system == "Linux" and machine in {"aarch64", "arm64"}:
        print(
            "PardoX: NO DISPONIBLE en linux-aarch64; el pipeline principal "
            "(Polars) no se ve afectado"
        )
    else:
        print(f"PardoX: plataforma soportada ({system}-{machine})")
    return int(failed)


def start(args: argparse.Namespace) -> int:
    if doctor():
        return 1
    env = write_env()
    if env.get("POSTGRES_PORT") == "auto":
        raise RuntimeError(".env contiene POSTGRES_PORT=auto; elimínalo y vuelve a ejecutar start.")
    compose(env, "up", "-d", "postgres", "redis")
    for _ in range(30):
        health = run(
            ["docker", "inspect", "--format={{.State.Health.Status}}", "cafenorte-postgres"],
            check=False,
            capture=True,
        ).stdout.strip()
        if health == "healthy":
            break
        time.sleep(2)
    else:
        compose(env, "logs", "postgres", check=False)
        return 1
    os.environ.update(env)
    sync_database_roles(env)
    result = run(
        [sys.executable, "-m", "cafenorte.ingest"],
        check=False,
        capture=True,
    )
    if result.returncode:
        report_ingest_failure(result.stderr or "")
        return 1
    print(result.stdout, end="")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(
            "ERROR: la ingesta no devolvió un resultado válido. "
            "Ejecuta `uv run cafenorte reset --yes` y vuelve a iniciar.",
            file=sys.stderr,
        )
        return 1
    if payload.get("load_mode") != "skipped":
        anchor = run(
            [
                "docker",
                "compose",
                "--env-file",
                str(ENV_PATH),
                "exec",
                "-T",
                "postgres",
                "sh",
                "-c",
                psql_command(ANCHOR_DATE_SQL, readonly=True),
            ],
            capture=True,
        ).stdout.strip()
        print(f"anchor_date={anchor}")
        run(
            [
                "uv",
                "run",
                "dbt",
                "build",
                "--project-dir",
                "dbt",
                "--profiles-dir",
                "dbt",
                "--target-path",
                "../artifacts/evidence/dbt",
                "--vars",
                json.dumps({"anchor_date": f"'{anchor}'"}),
            ]
        )
        run([sys.executable, "-m", "cafenorte.export_answers"])
    else:
        print("No source changed; dbt build and answer export skipped.")
    compose(env, "up", "-d", "superset")
    for _ in range(30):
        health = run(
            ["docker", "inspect", "--format={{.State.Health.Status}}", "cafenorte-superset"],
            check=False,
            capture=True,
        ).stdout.strip()
        if health == "healthy":
            break
        time.sleep(2)
    else:
        compose(env, "logs", "superset", check=False)
        return 1
    status()
    run([sys.executable, "scripts/run_report.py", "--no-browser"])
    if not args.no_browser and os.environ.get("CI", "").lower() != "true":
        superset_url = (
            f"http://127.0.0.1:{env['SUPERSET_PORT']}"
            "/superset/dashboard/cafenorte-4-respuestas/"
        )
        open_browser_target(superset_url)
        open_browser_target((ROOT / "artifacts/reports/run_report.html").resolve().as_uri())
    print_superset(args.show_credentials, env)
    return 0


def open_browser_target(uri: str) -> None:
    if webbrowser.open(uri):
        return
    if sys.platform == "darwin":
        command = ["open", uri]
    elif os.name == "nt":
        try:
            os.startfile(uri)  # type: ignore[attr-defined]
            return
        except OSError:
            command = []
    elif "microsoft" in platform.uname().release.lower():
        command = ["wslview", uri]
    else:
        command = ["xdg-open", uri]
    try:
        if command and subprocess.run(command, check=False).returncode == 0:
            return
    except OSError:
        pass
    print(f"No se pudo abrir automáticamente: {uri}")


def print_superset(show: bool, env: dict[str, str]) -> None:
    print("\n===== Superset listo =====")
    print(
        f"URL:        http://127.0.0.1:{env['SUPERSET_PORT']}/superset/dashboard/cafenorte-4-respuestas/"
    )
    print("Usuarios:   director      (ve toda la red, incluido ONLINE)")
    print("            gerente_t001  (solo tienda T001 en P2/P3/P4)")
    print("            admin         (solo administración)")
    if show:
        passwords = [
            "Contraseñas:",
            f"  admin:        {env['SUPERSET_ADMIN_PASSWORD']}",
            f"  director:     {env['DIRECTOR_PASSWORD']}",
            f"  gerente_t001: {env['GERENTE_T001_PASSWORD']}",
        ]
        print("\n".join(passwords))
    else:
        print("Contraseñas: ./scripts/credentials.sh (o start.sh --show-credentials)")
    print(
        "Reporte (usuarios y contraseñas con botón Mostrar): "
        f"{ROOT / 'artifacts/reports/run_report.html'}"
    )


def credentials() -> int:
    if not ENV_PATH.exists():
        print(f"No existe {ENV_PATH}. Ejecuta start para generarlo.", file=sys.stderr)
        return 1
    env = load_env()
    print(
        f"Superset: http://127.0.0.1:{env['SUPERSET_PORT']}/superset/dashboard/cafenorte-4-respuestas/\n"
    )
    print("Usuario           Rol                          Contraseña")
    for user, role, key in [
        ("admin", "Administración", "SUPERSET_ADMIN_PASSWORD"),
        ("director", "Toda la red, incluido ONLINE", "DIRECTOR_PASSWORD"),
        ("gerente_t001", "T001 en P2/P3/P4", "GERENTE_T001_PASSWORD"),
    ]:
        print(f"{user:<18}{role:<29}{env.get(key, '')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="cafenorte")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    for name in ("stop", "status", "validate", "credentials", "report"):
        sub.add_parser(name)
    start_parser = sub.add_parser("start")
    start_parser.add_argument("--no-browser", action="store_true")
    start_parser.add_argument("--show-credentials", action="store_true")
    restart_parser = sub.add_parser("restart")
    restart_parser.add_argument("--no-browser", action="store_true")
    restart_parser.add_argument("--show-credentials", action="store_true")
    reset_parser = sub.add_parser("reset")
    reset_parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    if args.command == "doctor":
        return doctor()
    if args.command == "start":
        return start(args)
    if args.command == "restart":
        stop(args)
        return start(args)
    if args.command == "credentials":
        return credentials()
    if args.command == "stop":
        return stop(args)
    if args.command == "reset":
        if not args.yes:
            print("No changes made. Re-run with --yes to confirm.")
            return 2
        compose(load_env(), "down", "--volumes", "--remove-orphans")
        return 0
    if args.command == "report":
        return run([sys.executable, "scripts/run_report.py"]).returncode
    if args.command == "status":
        return status()
    if args.command == "validate":
        return validate()
    raise AssertionError(args.command)


def stop(_: argparse.Namespace) -> int:
    if not ENV_PATH.exists():
        print("Missing .env; nothing was stopped.", file=sys.stderr)
        return 1
    return compose(load_env(), "stop").returncode


def status() -> int:
    if not ENV_PATH.exists():
        print("Missing .env; Compose status cannot be resolved.", file=sys.stderr)
        return 1
    env = load_env()
    health = (
        run(
            ["docker", "inspect", "--format={{.State.Health.Status}}", "cafenorte-postgres"],
            check=False,
            capture=True,
        ).stdout.strip()
        or "not-created"
    )
    print("PostgreSQL host: 127.0.0.1")
    print(f"PostgreSQL port: {env.get('POSTGRES_PORT', '')}")
    print(f"Health: {health}")
    print(f"Superset URL: http://127.0.0.1:{env.get('SUPERSET_PORT', '')}")
    print("Superset users: admin, director, gerente_t001 (passwords are in .env)")
    compose(env, "ps", "postgres", check=False)
    compose(env, "ps", "redis", "superset", check=False)
    if health != "healthy":
        return 0
    print("PostgreSQL:")
    compose_exec(env, 'pg_isready --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"')
    print("Última corrida:")
    compose_exec(env, psql_command(LAST_RUN_SQL))
    print("Silver:")
    compose_exec(env, psql_command(SILVER_COUNTS_SQL))
    result_file = ROOT / "artifacts/evidence/dbt/run_results.json"
    dbt_result = "sin corridas"
    if result_file.exists():
        payload = json.loads(result_file.read_text(encoding="utf-8"))
        statuses = [item.get("status") for item in payload.get("results", [])]
        dbt_result = (
            f"{payload.get('metadata', {}).get('generated_at', 'sin fecha')} "
            f"PASS={statuses.count('pass')} WARN={statuses.count('warn')} "
            f"ERROR={statuses.count('error')}"
        )
    print(f"Último dbt: {dbt_result}")
    print("Gold (analytics):")
    compose_exec(env, psql_command(GOLD_COUNTS_SQL))
    print(f"Reporte: {ROOT / 'artifacts/reports/run_report.html'}")
    return 0


def validate() -> int:
    if doctor():
        return 1
    if not ENV_PATH.exists():
        print("Missing .env. Run start first.", file=sys.stderr)
        return 1
    env = load_env()
    os.environ.update(env)
    checksum = (
        ["shasum", "-a", "256", "-c", "SHA256SUMS"]
        if platform.system() == "Darwin"
        else ["sha256sum", "-c", "SHA256SUMS"]
    )
    if platform.system() not in {"Darwin", "Linux"}:
        print("Unsupported platform for source checksum verification.", file=sys.stderr)
        return 1
    if run(checksum, check=False, capture=True, cwd=ROOT / "datos").returncode:
        print("fuente original del cliente modificada", file=sys.stderr)
        return 1
    shell_files = list((ROOT / "scripts").glob("*.sh")) + list(
        (ROOT / "docker/postgres/init").glob("*.sh")
    )
    for path in shell_files:
        if run(["bash", "-n", str(path)], check=False).returncode:
            return 1
    if shutil.which("shellcheck") is None and platform.system() != "Windows":
        print("shellcheck is required but not installed.", file=sys.stderr)
        return 1
    if shutil.which("shellcheck"):
        run(["shellcheck", *(str(path) for path in shell_files)])
    compose(env, "config", "--quiet")
    compose_exec(env, psql_command(SCHEMAS_ROLES_SQL))
    for service, container in (("Superset", "cafenorte-superset"), ("Redis", "cafenorte-redis")):
        health = run(
            ["docker", "inspect", "--format={{.State.Health.Status}}", container],
            check=False,
            capture=True,
        ).stdout.strip()
        if health != "healthy":
            print(f"{service} is not healthy.", file=sys.stderr)
            return 1
    anchor = compose_exec(
        env,
        psql_command(ANCHOR_DATE_SQL, readonly=True),
        capture=True,
    ).stdout.strip()
    if not anchor or len(anchor) != 10:
        print(f"Could not calculate anchor_date: {anchor}", file=sys.stderr)
        return 1
    print(f"anchor_date={anchor}")
    supported = platform.system() in {"Darwin", "Linux"} and platform.machine() in {
        "arm64",
        "x86_64",
        "amd64",
    }
    if supported:
        try:
            run(["uv", "run", "python", "-m", "cafenorte.ingest", "--engine", "pardox", "--force"])
        except subprocess.CalledProcessError:
            supported = False
            print(f"PardoX: UNSUPPORTED_PLATFORM ({platform.system()}-{platform.machine()})")
    else:
        print(f"PardoX: UNSUPPORTED_PLATFORM ({platform.system()}-{platform.machine()})")
    run(
        [
            "uv",
            "run",
            "dbt",
            "build",
            "--project-dir",
            "dbt",
            "--profiles-dir",
            "dbt",
            "--target-path",
            "../artifacts/evidence/dbt",
            "--vars",
            json.dumps({"anchor_date": f"'{anchor}'"}),
        ]
    )
    run(
        ["uv", "run", "pytest"]
        if supported
        else ["uv", "run", "pytest", "--ignore=tests/test_engines.py"]
    )
    run(["uv", "run", "python", "superset/test_rls.py"])
    run(["uv", "run", "ruff", "check", "."])
    run(["uv", "run", "python", "-m", "cafenorte.export_answers"])
    (ROOT / "artifacts/reports").mkdir(parents=True, exist_ok=True)
    (ROOT / "artifacts/reports/last_validate.txt").write_text(
        f"validate.sh: PASS ({time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
