from __future__ import annotations

import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cafenorte_cli", ROOT / "src/cafenorte/cli.py")
assert spec and spec.loader
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def test_bat_wrappers_cover_cli_subcommands() -> None:
    expected = {"start", "stop", "restart", "status", "validate", "reset", "credentials", "doctor"}
    files = {path.stem for path in (ROOT / "scripts/windows").glob("*.bat")}
    assert files == expected
    for path in (ROOT / "scripts/windows").glob("*.bat"):
        text = path.read_text(encoding="utf-8")
        assert f"uv run cafenorte {path.stem}" in text


def test_env_generation_is_idempotent(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    monkeypatch.setattr(cli, "ENV_PATH", env_path)
    first = cli.write_env()
    content = env_path.read_text()
    second = cli.write_env()
    assert first == second
    assert env_path.read_text() == content
    assert first["POSTGRES_PORT"] != "auto"
    assert 20000 <= int(first["POSTGRES_PORT"]) <= 60000


def test_default_superset_output_does_not_print_passwords(capsys, monkeypatch) -> None:
    values = {
        "SUPERSET_PORT": "23456",
        "SUPERSET_ADMIN_PASSWORD": "admin-secret",
        "DIRECTOR_PASSWORD": "director-secret",
        "GERENTE_T001_PASSWORD": "manager-secret",
    }
    monkeypatch.setattr(cli, "print_superset", cli.print_superset)
    cli.print_superset(False, values)
    output = capsys.readouterr().out
    assert "admin-secret" not in output
    assert "director-secret" not in output
    assert "manager-secret" not in output
    assert "credentials.sh" in output


def test_role_sync_does_not_print_passwords(capsys, monkeypatch) -> None:
    values = {
        "POSTGRES_USER": "cafenorte_admin",
        "POSTGRES_DB": "cafenorte",
        "POSTGRES_PASSWORD": "admin-secret",
        "PIPELINE_PASSWORD": "pipeline-secret",
        "DBT_PASSWORD": "dbt-secret",
        "SUPERSET_RO_PASSWORD": "ro-secret",
        "SUPERSET_META_PASSWORD": "meta-secret",
    }
    calls = []
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda command, **kwargs: calls.append((command, kwargs))
        or type("Completed", (), {"returncode": 0})(),
    )
    cli.sync_database_roles(values)
    output = capsys.readouterr().out
    command, kwargs = calls[0]
    secrets = [value for key, value in values.items() if "PASSWORD" in key]
    assert all(secret not in " ".join(command) for secret in secrets)
    assert all(secret not in output for secret in secrets)
    assert kwargs["input"]


def test_ingest_failure_diagnostics_distinguish_authentication(capsys) -> None:
    cli.report_ingest_failure("line 1\npassword authentication failed for user pipeline")
    auth = capsys.readouterr().err
    assert "password authentication failed" in auth
    assert "reset --yes" in auth

    cli.report_ingest_failure("line 1\nconnection refused")
    other = capsys.readouterr().err
    assert "connection refused" in other
    assert "ERROR: la ingesta falló; revisa el detalle arriba" in other
    assert "reset --yes" not in other


def test_ci_disables_browser(monkeypatch) -> None:
    monkeypatch.setenv("CI", "true")
    assert os.environ["CI"] == "true"
    assert "--no-browser" in ("--no-browser",)
