import json
import os
import sys
import urllib.error
import urllib.request


def request(base, path, token, payload=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(f"{base}{path}", data=body, headers=headers)
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def login(base, username, password):
    return request(base, "/api/v1/security/login", None, {"username": username, "password": password, "provider": "db", "refresh": True})["access_token"]


def query_chart(base, token, item, columns):
    result = request(base, "/api/v1/chart/data", token, {"datasource": {"id": item["datasource_id"], "type": "table"}, "queries": [{"columns": columns, "metrics": [], "row_limit": 1000}], "result_format": "json", "result_type": "full"})
    return result["result"][0]["data"]


def main():
    base = f"http://127.0.0.1:{os.environ['SUPERSET_PORT']}"
    manager_token = login(base, "gerente_t001", os.environ["GERENTE_T001_PASSWORD"])
    director_token = login(base, "director", os.environ["DIRECTOR_PASSWORD"])
    director_charts = request(base, "/api/v1/chart/?q=(page:0,page_size:100)", director_token)["result"]
    if len(director_charts) < 5:
        raise AssertionError(f"dashboard must have at least five charts: {len(director_charts)}")
    by_name = {item["slice_name"]: item for item in director_charts}
    p3_manager = query_chart(base, manager_token, by_name["P3 · Crecimiento por canal"], ["channel"])
    p4_manager = query_chart(base, manager_token, by_name["P4 · Margen negativo"], ["tienda_id", "channel"])
    if not p3_manager or not all(row["channel"] == "T001" for row in p3_manager):
        raise AssertionError(f"manager P3 leaked rows: {p3_manager[:3]}")
    if not p4_manager or not all(row["tienda_id"] == "T001" for row in p4_manager):
        raise AssertionError(f"manager P4 leaked rows: {p4_manager[:3]}")
    p3_director = query_chart(base, director_token, by_name["P3 · Crecimiento por canal"], ["channel"])
    channels = {row["channel"] for row in p3_director}
    if len(channels) <= 1 or "ONLINE" not in channels:
        raise AssertionError(f"director P3 lacks network channels: {channels}")
    print(f"manager P3 rows={len(p3_manager)} channels=T001")
    print(f"manager P4 rows={len(p4_manager)} tienda_id=T001")
    print(f"director P3 rows={len(p3_director)} channels={sorted(channels)}")
    print(f"negative control: director without T001 rule sees {len(channels)} channels")
    print(f"dashboard charts={len(director_charts)}")
    print("Superset API data queries and RLS: PASS")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(exc.read().decode(), file=sys.stderr)
        raise
