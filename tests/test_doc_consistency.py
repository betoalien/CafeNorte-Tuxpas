import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_documentation_matches_current_decisions() -> None:
    proposal = (ROOT / "docs/PROPUESTA_AWS.md").read_text(encoding="utf-8")
    profiling = (ROOT / "artifacts/evidence/profiling.md").read_text(encoding="utf-8")
    assert "es el maestro aunque" not in proposal
    assert "es el maestro aunque" not in profiling
    assert "pregunta abierta al cliente" not in proposal
    assert "pregunta abierta al cliente" not in profiling

    model_names = {
        path.stem
        for path in (ROOT / "dbt/models").rglob("*.sql")
        if "/marts/" in str(path)
    }
    metrics = (ROOT / "docs/BUSINESS_METRICS.md").read_text(encoding="utf-8")
    for reference in re.findall(r"analytics\.([a-z0-9_]+)", metrics):
        assert reference in model_names, reference

    for path in ROOT.rglob("*.md"):
        if "artifacts/evidence/block-" in str(path):
            continue
        assert "Streamlit y Tableau consumen" not in path.read_text(encoding="utf-8")

    final_validation = (ROOT / "artifacts/evidence/final-validation.md").read_text(
        encoding="utf-8"
    )
    assert "gitleaks no estaba instalado" not in final_validation

    assert "Bloque" not in (
        ROOT / "artifacts/evidence/answers/README.md"
    ).read_text(encoding="utf-8")
    assert "conservador" in proposal.lower()
