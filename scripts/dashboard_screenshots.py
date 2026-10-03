"""Smoke-test and capture the local Superset dashboards."""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts/reports/dashboards"


def capture(page, port, username, password, slug):
    page.goto(f"http://127.0.0.1:{port}/logout/", wait_until="networkidle")
    page.goto(f"http://127.0.0.1:{port}/login/", wait_until="networkidle")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(password)
    page.locator('input[type="submit"]').click()
    page.goto(
        f"http://127.0.0.1:{port}/superset/dashboard/{slug}/",
        wait_until="networkidle",
    )
    page.get_by_text("CaféNorte", exact=False).first.wait_for(timeout=60000)
    page.locator(".loading, .ant-spin-spinning").wait_for(state="detached", timeout=60000)
    body = page.locator("body").inner_text()
    if "Unexpected error" in body or "Error:" in body:
        raise AssertionError(f"dashboard {slug} rendered an error")
    if "No results were returned" in body and slug != "cafenorte-mi-tienda":
        raise AssertionError(f"dashboard {slug} rendered an unexpected empty result")
    page.screenshot(path=str(OUTPUT / f"{username}-{slug}.png"), full_page=True)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        port = os.environ["SUPERSET_PORT"]
        capture(
            page, port, "director", os.environ["DIRECTOR_PASSWORD"], "cafenorte-4-respuestas"
        )
        capture(
            page, port, "director", os.environ["DIRECTOR_PASSWORD"], "cafenorte-calidad-datos"
        )
        capture(
            page, port, "gerente_t001", os.environ["GERENTE_T001_PASSWORD"], "cafenorte-mi-tienda"
        )
        browser.close()
    print(f"Dashboard screenshots: {OUTPUT}")


if __name__ == "__main__":
    main()
