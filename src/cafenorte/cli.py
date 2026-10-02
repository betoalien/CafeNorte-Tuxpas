"""Cross-platform orchestration CLI for the CaféNorte local stack."""
# ruff: noqa: E501

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


def load_env(path: Path | None = None) -> dict[str, str]:
    path = path or ENV_PATH
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"').strip("'")
    return values


def run(command: list[str], *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=check, text=True, capture_output=capture)


def compose(env: dict[str, str], *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["docker", "compose", "--env-file", str(ENV_PATH), *args], check=check)


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
    ENV_PATH.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
    secure_env()
    print(f"Generated .env with PostgreSQL port {values['POSTGRES_PORT']}.")
    return values


def secure_env() -> None:
    if os.name == "nt":
        username = os.environ.get("USERNAME", "")
        if username:
            run(["icacls", str(ENV_PATH), "/inheritance:r", "/grant:r", f"{username}:F"], check=False)
    else:
        ENV_PATH.chmod(0o600)


def doctor() -> int:
    system, machine = platform.system(), platform.machine()
    wsl = system == "Linux" and "microsoft" in Path("/proc/version").read_text(errors="ignore").lower() if Path("/proc/version").exists() else False
    print(f"Doctor: OS={system} arch={machine}{' WSL' if wsl else ''}")
    failed = False
    for command, fix in [("docker", "instala Docker Desktop o Docker Engine"), ("uv", "instala uv desde https://docs.astral.sh/uv/")]:
        if shutil.which(command) is None:
            print(f"ERROR: {command} no está instalado. Arreglo: {fix}", file=sys.stderr)
            failed = True
    if shutil.which("docker"):
        if run(["docker", "info"], check=False, capture=True).returncode:
            print("ERROR: el daemon de Docker no es accesible. En Linux: sudo usermod -aG docker $USER o sudo systemctl start docker.", file=sys.stderr)
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
        print("ERROR: WSL debe usar el filesystem Linux, no /mnt/; clona de nuevo dentro de WSL.", file=sys.stderr)
        failed = True
    if any("\r" in path.read_text(errors="ignore") for path in (ROOT / "scripts").glob("*.sh")):
        print("AVISO: hay CRLF en scripts/*.sh; clona de nuevo dentro de WSL.", file=sys.stderr)
    if system == "Darwin" and machine == "arm64":
        print("PardoX: soportado (probado)")
    elif system == "Darwin" and machine == "x86_64":
        print("PardoX: binario incluido en 0.3.4, no verificado (sin runners macOS Intel en CI)")
    elif system == "Linux" and machine in {"aarch64", "arm64"}:
        print("PardoX: NO DISPONIBLE en linux-aarch64; el pipeline principal (Polars) no se ve afectado")
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
        health = run(["docker", "inspect", "--format={{.State.Health.Status}}", "cafenorte-postgres"], check=False, capture=True).stdout.strip()
        if health == "healthy":
            break
        time.sleep(2)
    else:
        compose(env, "logs", "postgres", check=False)
        return 1
    os.environ.update(env)
    result = run([sys.executable, "-m", "cafenorte.ingest"], capture=True)
    print(result.stdout, end="")
    payload = json.loads(result.stdout)
    if payload.get("load_mode") != "skipped":
        anchor = run(["docker", "compose", "--env-file", str(ENV_PATH), "exec", "-T", "postgres", "sh", "-c", 'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -At -c "SELECT LEAST((SELECT max(fecha_hora_normalizada::date) FROM silver.pos_sales), (SELECT max(fecha::date) FROM silver.ecommerce_orders), (SELECT max(fecha) FROM silver.inventory_snapshots));"'], capture=True).stdout.strip()
        print(f"anchor_date={anchor}")
        run(["uv", "run", "dbt", "build", "--project-dir", "dbt", "--profiles-dir", "dbt", "--target-path", "../artifacts/evidence/dbt", "--vars", json.dumps({"anchor_date": anchor})])
        run([sys.executable, "-m", "cafenorte.export_answers"])
    else:
        print("No source changed; dbt build and answer export skipped.")
    compose(env, "up", "-d", "superset")
    run([sys.executable, "scripts/run_report.py", "--no-browser"])
    if not args.no_browser and os.environ.get("CI", "").lower() != "true":
        webbrowser.open(f"http://127.0.0.1:{env['SUPERSET_PORT']}/superset/dashboard/cafenorte-4-respuestas/")
    print_superset(args.show_credentials, env)
    return 0


def print_superset(show: bool, env: dict[str, str]) -> None:
    print("\n===== Superset listo =====")
    print(f"URL:        http://127.0.0.1:{env['SUPERSET_PORT']}/superset/dashboard/cafenorte-4-respuestas/")
    print("Usuarios:   director      (ve toda la red, incluido ONLINE)")
    print("            gerente_t001  (solo tienda T001 en P2/P3/P4)")
    print("            admin         (solo administración)")
    if show:
        print(f"Contraseñas:\n  admin:        {env['SUPERSET_ADMIN_PASSWORD']}\n  director:     {env['DIRECTOR_PASSWORD']}\n  gerente_t001: {env['GERENTE_T001_PASSWORD']}")
    else:
        print("Contraseñas: ./scripts/credentials.sh (o start.sh --show-credentials)")
    print(f"Reporte:    {ROOT / 'artifacts/reports/run_report.html'}")


def credentials() -> int:
    if not ENV_PATH.exists():
        print(f"No existe {ENV_PATH}. Ejecuta start para generarlo.", file=sys.stderr)
        return 1
    env = load_env()
    print(f"Superset: http://127.0.0.1:{env['SUPERSET_PORT']}/superset/dashboard/cafenorte-4-respuestas/\n")
    print("Usuario           Rol                          Contraseña")
    for user, role, key in [("admin", "Administración", "SUPERSET_ADMIN_PASSWORD"), ("director", "Toda la red, incluido ONLINE", "DIRECTOR_PASSWORD"), ("gerente_t001", "T001 en P2/P3/P4", "GERENTE_T001_PASSWORD")]:
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
    print("PostgreSQL:")
    compose(env, "ps", check=False)
    print(f"Superset URL: http://127.0.0.1:{env.get('SUPERSET_PORT', '')}")
    print("Superset users: admin, director, gerente_t001 (passwords are in .env)")
    print("Silver: 7 tablas")
    print("Gold (analytics): 5 marts")
    print(f"Reporte: {ROOT / 'artifacts/reports/run_report.html'}")
    return 0


def validate() -> int:
    if doctor():
        return 1
    if not ENV_PATH.exists():
        print("Missing .env. Run start first.", file=sys.stderr)
        return 1
    os.environ.update(load_env())
    shell_files = list((ROOT / "scripts").glob("*.sh")) + list((ROOT / "docker/postgres/init").glob("*.sh"))
    for path in shell_files:
        if run(["bash", "-n", str(path)], check=False).returncode:
            return 1
    if shutil.which("shellcheck") is None and platform.system() != "Windows":
        print("shellcheck is required but not installed.", file=sys.stderr)
        return 1
    if shutil.which("shellcheck"):
        run(["shellcheck", *(str(path) for path in shell_files)])
    return run(["uv", "run", "pytest"]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
