#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

os="$(uname -s)"
arch="$(uname -m)"
wsl=0
if [[ "$os" == "Linux" ]] && [[ -r /proc/version ]] && grep -qi microsoft /proc/version; then
  wsl=1
fi
wsl_label=""
if [[ "$wsl" -eq 1 ]]; then wsl_label=" WSL"; fi
echo "Doctor: OS=$os arch=$arch$wsl_label"

fail=0
require_command() {
  local command_name="$1"
  local suggestion="$2"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "ERROR: $command_name no está instalado. Arreglo: $suggestion" >&2
    fail=1
  fi
}

require_command docker "instala Docker Desktop o Docker Engine"
if command -v docker >/dev/null 2>&1; then
  if ! docker info >/dev/null 2>&1; then
    echo "ERROR: el daemon de Docker no es accesible. En Linux: sudo usermod -aG docker \$USER y vuelve a iniciar sesión, o sudo systemctl start docker." >&2
    fail=1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    echo "ERROR: se requiere Docker Compose v2. Actualiza Docker Desktop o instala el plugin Compose v2." >&2
    fail=1
  else
    echo "OK: Docker Compose v2"
  fi
fi
require_command uv "instala uv desde https://docs.astral.sh/uv/"
require_command openssl "instala OpenSSL con el gestor de paquetes del sistema"
require_command shellcheck "instala ShellCheck con brew/apt/dnf"
if [[ "$os" == "Darwin" ]]; then
  require_command lsof "instala lsof"
elif [[ "$os" == "Linux" ]]; then
  if ! command -v ss >/dev/null 2>&1 && ! command -v netstat >/dev/null 2>&1; then
    echo "ERROR: instala ss (iproute2) o netstat para comprobar puertos libres." >&2
    fail=1
  fi
fi

if [[ "$wsl" -eq 1 ]] && [[ "$project_root" == /mnt/* ]]; then
  echo "ERROR: WSL debe ejecutar el repositorio dentro del filesystem Linux, no bajo /mnt/. Docker y permisos 600 son más fiables allí; clona de nuevo dentro de WSL." >&2
  fail=1
fi

if grep -Il "$(printf '\r')" scripts/*.sh >/dev/null 2>&1; then
  echo "AVISO: hay CRLF en scripts/*.sh; clona de nuevo dentro de WSL para restaurar finales LF." >&2
fi

case "$os/$arch" in
  Darwin/arm64)
    echo "PardoX: soportado (probado)" ;;
  Darwin/x86_64)
    echo "PardoX: binario incluido en 0.3.4, no verificado (sin runners macOS Intel en CI)" ;;
  Linux/x86_64|MINGW*/x86_64|MSYS*/x86_64|CYGWIN*/x86_64)
    echo "PardoX: plataforma soportada ($os-$arch)" ;;
  Linux/aarch64|Linux/arm64)
    echo "PardoX: NO DISPONIBLE en linux-aarch64; el pipeline principal (Polars) no se ve afectado"
    ;;
  *)
    echo "PardoX: UNSUPPORTED_PLATFORM (${os}-${arch})"
    ;;
esac

exit "$fail"
