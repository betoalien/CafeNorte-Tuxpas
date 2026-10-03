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
    return request(
        base,
        "/api/v1/security/login",
        None,
        {"username": username, "password": password, "provider": "db", "refresh": True},
    )["access_token"]


def query_chart(base, token, item, columns):
    result = request(
        base,
        "/api/v1/chart/data",
        token,
        {
            "datasource": {"id": item["datasource_id"], "type": "table"},
            "queries": [{"columns": columns, "metrics": [], "row_limit": 1000}],
            "result_format": "json",
            "result_type": "full",
        },
    )
    return result["result"][0]["data"]


def dashboard_positions(base, token, slug):
    dashboard = request(base, f"/api/v1/dashboard/{slug}", token)
    positions = json.loads(dashboard["result"]["position_json"])
    if "ROOT_ID" not in positions or "GRID_ID" not in positions:
        raise AssertionError("dashboard layout lacks ROOT_ID or GRID_ID")
    return positions


def chart_nodes(positions):
    return {
        key: node for key, node in positions.items() if key.startswith("CHART-")
    }


def assert_denied(call):
    try:
        call()
    except urllib.error.HTTPError as exc:
        if exc.code not in (403, 404):
            raise
        return
    raise AssertionError("manager unexpectedly accessed a network resource")


def main():
    base = f"http://127.0.0.1:{os.environ['SUPERSET_PORT']}"
    manager_token = login(base, "gerente_t001", os.environ["GERENTE_T001_PASSWORD"])
    director_token = login(base, "director", os.environ["DIRECTOR_PASSWORD"])
    director_positions = dashboard_positions(
        base, director_token, "cafenorte-4-respuestas"
    )
    manager_positions = dashboard_positions(base, manager_token, "cafenorte-mi-tienda")
    if len(chart_nodes(director_positions)) != 10:
        raise AssertionError("director dashboard must contain ten charts")
    if len(chart_nodes(manager_positions)) != 4:
        raise AssertionError("manager dashboard must contain four charts")
    assert_denied(
        lambda: request(
            base, "/api/v1/dashboard/cafenorte-4-respuestas", manager_token
        )
    )
    dashboard_positions(base, director_token, "cafenorte-calidad-datos")
    assert_denied(
        lambda: request(
            base, "/api/v1/dashboard/cafenorte-calidad-datos", manager_token
        )
    )
    director_charts = request(
        base, "/api/v1/chart/?q=(page:0,page_size:100)", director_token
    )["result"]
    by_name = {item["slice_name"]: item for item in director_charts}
    manager_charts = request(
        base, "/api/v1/chart/?q=(page:0,page_size:100)", manager_token
    )["result"]
    manager_by_name = {item["slice_name"]: item for item in manager_charts}
    for network_name in (
        "P1 · Rotación top 10", "P3 · Físico vs e-commerce", "Reconciliación de fuentes"
    ):
        assert_denied(lambda name=network_name: query_chart(
            base, manager_token, by_name[name], ["product_id"]
        ))
    p1_manager = query_chart(
        base, manager_token, manager_by_name["P1 · Rotación mi tienda"], ["tienda_id", "product_id"]
    )
    p2_manager = query_chart(
        base, manager_token, manager_by_name["P2 · Stockouts > 3 días"], ["tienda_id", "product_id"]
    )
    p3_manager = query_chart(
        base, manager_token, manager_by_name["P3 · Crecimiento por canal"], ["channel"]
    )
    p4_manager = query_chart(
        base,
        manager_token,
        manager_by_name["P4 · Margen negativo"],
        ["product_id", "tienda_id", "channel"],
    )
    if not p1_manager or not all(row["tienda_id"] == "T001" for row in p1_manager):
        raise AssertionError(f"manager P1 leaked rows: {p1_manager[:3]}")
    if not p3_manager or not all(row["channel"] == "T001" for row in p3_manager):
        raise AssertionError(f"manager P3 leaked rows: {p3_manager[:3]}")
    if not p4_manager or not all(row["tienda_id"] == "T001" for row in p4_manager):
        raise AssertionError(f"manager P4 leaked rows: {p4_manager[:3]}")
    if p2_manager:
        raise AssertionError(f"manager P2 should have zero rows: {p2_manager[:3]}")
    p2_director = query_chart(
        base, director_token, by_name["P2 · Stockouts > 3 días"], ["tienda_id", "product_id"]
    )
    if len(p2_director) != 3:
        raise AssertionError(f"director P2 expected three rows: {p2_director[:3]}")
    p4_director = query_chart(
        base, director_token, by_name["P4 · Margen negativo"], ["product_id", "tienda_id"]
    )
    if len(p4_director) != 120:
        raise AssertionError(f"director P4 expected 120 rows: {len(p4_director)}")
    p3_director = query_chart(
        base, director_token, by_name["P3 · Crecimiento por canal"], ["channel"]
    )
    channels = {row["channel"] for row in p3_director}
    if len(channels) <= 1 or "ONLINE" not in channels:
        raise AssertionError(f"director P3 lacks network channels: {channels}")
    print(f"manager P1 rows={len(p1_manager)} tienda_id=T001")
    print(f"manager P3 rows={len(p3_manager)} channels=T001")
    print(f"manager P4 rows={len(p4_manager)} tienda_id=T001")
    print(f"manager P2 rows={len(p2_manager)} (expected zero)")
    print(f"director P2 rows={len(p2_director)} (expected three)")
    print(f"director P4 rows={len(p4_director)} (expected 120)")
    print(f"director P3 rows={len(p3_director)} channels={sorted(channels)}")
    print(f"negative control: director without T001 rule sees {len(channels)} channels")
    print(f"network dashboard charts={len(chart_nodes(director_positions))}")
    print("director dashboard access for manager: denied (HTTP 403/404)")
    print("Superset API data queries and RLS: PASS")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(exc.read().decode(), file=sys.stderr)
        raise
