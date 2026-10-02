import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def post(url, payload):
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def main():
    base = f"http://127.0.0.1:{os.environ['SUPERSET_PORT']}"
    visible = {}
    for username, password in (("gerente_t001", os.environ["GERENTE_T001_PASSWORD"]), ("director", os.environ["SUPERSET_ADMIN_PASSWORD"])):
        token = post(f"{base}/api/v1/security/login", {"username": username, "password": password, "provider": "db", "refresh": True})["access_token"]
        request = urllib.request.Request(f"{base}/api/v1/dashboard/?q=(page:0,page_size:100)", headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(request) as response:
            dashboards = json.load(response)
        visible[username] = [item.get("slug") for item in dashboards.get("result", [])]
    if "cafenorte-4-respuestas" not in visible["director"]:
        raise AssertionError(f"dashboard missing for director: {visible}")
    rules = Path(__file__).with_name("rls.yaml").read_text()
    for table in ("mart_stockouts_over_3_days", "mart_monthly_channel_growth", "mart_negative_margin_products"):
        if table not in rules:
            raise AssertionError(f"missing RLS table rule: {table}")
    if "tienda_id = 'T001'" not in rules:
        raise AssertionError("missing T001 RLS clause")
    print("Superset API login, dashboard import, and T001 RLS declaration: PASS")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(exc.read().decode(), file=sys.stderr)
        raise
