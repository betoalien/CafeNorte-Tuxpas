from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cafenorte_cli", ROOT / "src/cafenorte/cli.py")
assert spec and spec.loader
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


EXPECTED = {
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


def test_cli_step_plan_matches_bash_reference() -> None:
    for command, expected in EXPECTED.items():
        actual = cli.step_plan(command)
        missing = [step for step in expected if step not in actual]
        assert not missing, f"{command}: faltan pasos {missing}"
        assert actual == expected, f"{command}: orden distinto; actual={actual}"


def test_browser_opens_superset_then_report(monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(cli.webbrowser, "open", lambda uri: opened.append(uri) or True)
    superset = "http://127.0.0.1:59038/superset/dashboard/cafenorte-4-respuestas/"
    report = (ROOT / "artifacts/reports/run_report.html").resolve().as_uri()

    cli.open_browser_target(superset)
    cli.open_browser_target(report)

    assert opened == [superset, report]


def test_start_browser_policy_for_flags_and_ci(monkeypatch) -> None:
    env = {
        "POSTGRES_PORT": "23779",
        "SUPERSET_PORT": "59038",
        "POSTGRES_DB": "cafenorte",
        "POSTGRES_USER": "pipeline",
        "PIPELINE_USER": "pipeline",
        "PIPELINE_PASSWORD": "secret",
        "SUPERSET_ADMIN_PASSWORD": "secret",
        "DIRECTOR_PASSWORD": "secret",
        "GERENTE_T001_PASSWORD": "secret",
    }
    monkeypatch.setattr(cli, "doctor", lambda: 0)
    monkeypatch.setattr(cli, "write_env", lambda: env)
    monkeypatch.setattr(cli, "compose", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "status", lambda: 0)

    def fake_run(command, **kwargs):
        if "inspect" in command:
            return subprocess.CompletedProcess(command, 0, "healthy\n", "")
        if any("ingest" in part for part in command):
            return subprocess.CompletedProcess(command, 0, json.dumps({"load_mode": "skipped"}), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(cli, "run", fake_run)
    opened: list[str] = []
    monkeypatch.setattr(cli, "open_browser_target", opened.append)

    original = {key: os.environ.get(key) for key in env}
    try:
        for args, ci, expected in (
            (argparse.Namespace(no_browser=True, show_credentials=False), "", 0),
            (argparse.Namespace(no_browser=False, show_credentials=False), "true", 0),
            (argparse.Namespace(no_browser=False, show_credentials=False), "", 2),
        ):
            opened.clear()
            monkeypatch.setenv("CI", ci)
            assert cli.start(args) == 0
            assert len(opened) == expected
            if expected:
                assert opened[0].startswith("http://127.0.0.1:59038/")
                assert opened[1].endswith("/artifacts/reports/run_report.html")
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
