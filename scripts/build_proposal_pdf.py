"""Render the AWS proposal as a compact, reproducible PDF when Chrome is available."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/PROPUESTA_AWS.md"
OUTPUT = ROOT / "artifacts/evidence/PROPUESTA_AWS.pdf"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

CSS = """
@page { size: Letter; margin: 2cm; }
body { font-family: system-ui, -apple-system, sans-serif; font-size: 10.5pt;
       line-height: 1.22; color: #17202a; }
h1 { font-size: 18pt; margin: 0 0 8pt; } h2 { font-size: 13pt; margin: 11pt 0 4pt; }
h2 { break-after: avoid; page-break-after: avoid; }
p { margin: 4pt 0; } ul { margin: 4pt 0; padding-left: 18pt; }
pre { font: 9pt ui-monospace, SFMono-Regular, monospace; border: 1px solid #aaa;
      padding: 6pt; white-space: pre-wrap; page-break-inside: avoid; break-inside: avoid; }
table { border-collapse: collapse; width: 100%; margin: 5pt 0;
        page-break-inside: avoid; break-inside: avoid; }
th, td { border: .5pt solid #888; padding: 3pt 4pt; }
th { background: #e9eef2; } a { color: #145a86; }
.phase-table th:nth-child(1), .phase-table td:nth-child(1) { width: 8%; text-align: center; }
.phase-table th:nth-child(2), .phase-table td:nth-child(2) { width: 42%; }
.phase-table th:nth-child(3), .phase-table td:nth-child(3) { width: 50%; }
"""


def markdown_html() -> str:
    try:
        import markdown
    except ImportError as error:
        raise SystemExit(
            "Falta markdown: ejecuta uv run --with markdown python scripts/build_proposal_pdf.py"
        ) from error
    body = markdown.markdown(
        SOURCE.read_text(encoding="utf-8"), extensions=["tables", "fenced_code"]
    )
    html = (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'><style>"
        + CSS
        + f"</style></head><body>{body}</body></html>"
    )
    return html.replace(
        "<table>\n<thead>\n<tr>\n<th>Fase",
        "<table class='phase-table'>\n<thead>\n<tr>\n<th>Fase",
    )


def verify_pdf_text(pdf_path: Path) -> None:
    pdftotext = shutil.which("pdftotext")
    if pdftotext is None:
        print("pdftotext no disponible; se omite la verificacion de layout textual.")
        return
    with tempfile.TemporaryDirectory() as temporary:
        text_path = Path(temporary) / "proposal.txt"
        subprocess.run(
            [pdftotext, "-layout", str(pdf_path), str(text_path)], check=True
        )
        text = text_path.read_text(encoding="utf-8")
    if len(re.findall(r"\bFase\b", text)) != 1:
        raise SystemExit("La tabla de fases aparece partida o tiene encabezados duplicados.")
    for phase in ("1", "2", "3", "4"):
        if not any(line.lstrip().startswith(f"{phase} ") for line in text.splitlines()):
            raise SystemExit(f"Falta la fila de fase {phase} en el texto extraido.")
    if sum(line.lstrip().startswith(tuple(f"{phase} " for phase in ("1", "2", "3", "4")))
           for line in text.splitlines()) != 4:
        raise SystemExit("Una fila de fases se partio en varias lineas.")


def chrome_path() -> Path | None:
    candidates = [
        CHROME,
        Path(shutil.which("google-chrome") or ""),
        Path(shutil.which("chromium") or ""),
        Path(shutil.which("chromium-browser") or ""),
    ]
    return next((path for path in candidates if str(path) and path.exists()), None)


def main() -> int:
    browser = chrome_path()
    if browser is None:
        print("Chrome/Chromium no disponible; se omite la exportación PDF.")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        html_path = Path(temporary) / "proposal.html"
        html_path.write_text(markdown_html(), encoding="utf-8")
        subprocess.run(
            [
                str(browser), "--headless", "--disable-gpu", "--no-sandbox",
                "--no-pdf-header-footer", f"--print-to-pdf={OUTPUT}",
                html_path.as_uri(),
            ],
            check=True,
        )
    verify_pdf_text(OUTPUT)
    print(f"PDF generado: {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
