from __future__ import annotations

# ruff: noqa: E501
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cafenorte_cli", ROOT / "src/cafenorte/cli.py")
assert spec and spec.loader
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


EXPECTED = {
    "start": ["doctor", "env", "compose postgres redis", "postgres healthy", "ingest", "anchor_date", "dbt build", "export answers", "superset healthy", "status", "report"],
    "restart": ["stop", "start"],
    "stop": ["compose stop"],
    "status": ["pg_isready", "run_log", "silver counts", "dbt result", "gold counts", "report path"],
    "validate": ["doctor", "source checksums", "bash -n", "shellcheck", "compose config", "schemas roles superset_meta", "anchor_date", "pardox force", "dbt build", "pytest", "superset RLS", "ruff", "export answers"],
    "reset": ["compose down volumes"],
    "credentials": ["read .env", "print credentials"],
    "doctor": ["platform", "docker", "compose v2", "uv", "shellcheck", "port tool", "pardox platform"],
}


def test_cli_step_plan_matches_bash_reference() -> None:
    for command, expected in EXPECTED.items():
        actual = cli.step_plan(command)
        missing = [step for step in expected if step not in actual]
        assert not missing, f"{command}: faltan pasos {missing}"
        assert actual == expected, f"{command}: orden distinto; actual={actual}"
