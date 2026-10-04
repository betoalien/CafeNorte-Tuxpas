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
    return {key: node for key, node in positions.items() if key.startswith("CHART-")}


def assert_denied(call):
    try:
        call()
    except urllib.error.HTTPError as exc:
        if exc.code not in (403, 404):
            raise
        return
    raise AssertionError("manager unexpectedly accessed a network resource")


def close(value, expected, tolerance):
    if value is None or abs(float(value) - expected) > tolerance:
        raise AssertionError(f"expected {expected}, got {value}")


def main():
    base = f"http://127.0.0.1:{os.environ['SUPERSET_PORT']}"
    manager_token = login(base, "gerente_t001", os.environ["GERENTE_T001_PASSWORD"])
    director_token = login(base, "director", os.environ["DIRECTOR_PASSWORD"])
    director_positions = dashboard_positions(base, director_token, "cafenorte-4-respuestas")
    manager_positions = dashboard_positions(base, manager_token, "cafenorte-mi-tienda")
    dashboard_positions(base, director_token, "cafenorte-calidad-datos")
    director_count = len(chart_nodes(director_positions))
    manager_count = len(chart_nodes(manager_positions))
    if director_count != 12:
        raise AssertionError(f"director dashboard must contain 12 charts, found {director_count}")
    if manager_count != 8:
        raise AssertionError(f"manager dashboard must contain 8 charts, found {manager_count}")
    for slug in ("cafenorte-4-respuestas", "cafenorte-calidad-datos"):
        assert_denied(lambda slug=slug: request(base, f"/api/v1/dashboard/{slug}", manager_token))

    director_charts = request(base, "/api/v1/chart/?q=(page:0,page_size:100)", director_token)[
        "result"
    ]
    by_name = {item["slice_name"]: item for item in director_charts}
    manager_charts = request(base, "/api/v1/chart/?q=(page:0,page_size:100)", manager_token)[
        "result"
    ]
    manager_by_name = {item["slice_name"]: item for item in manager_charts}

    for network_name in (
        "Ventas 12 meses (MXN)",
        "P1 · ¿Qué productos rotan más en la red?",
        "P3 · ¿Crece el negocio y por qué canal?",
        "Calidad · Conciliación por fuente",
    ):
        assert_denied(
            lambda name=network_name: query_chart(base, manager_token, by_name[name], ["*"])
        )

    red = query_chart(
        base,
        director_token,
        by_name["Ventas 12 meses (MXN)"],
        [
            "ventas_12m",
            "fisico_abr_mar",
            "ecommerce_abr_mar",
            "ecommerce_share",
            "perdida_margen",
            "tiendas_quiebre",
        ],
    )[0]
    close(red["ventas_12m"], 24949918.21, 0.5)
    close(red["fisico_abr_mar"], 0.027, 0.0005)
    close(red["ecommerce_abr_mar"], -0.0847, 0.0005)
    close(red["ecommerce_share"], 0.1695, 0.0005)
    close(red["perdida_margen"], -218475.56, 0.5)
    close(red["tiendas_quiebre"], 3, 0)

    store = query_chart(
        base,
        manager_token,
        manager_by_name["Mi tienda · Ventas 12 meses (MXN)"],
        ["tienda_id", "ventas_12m", "crecimiento_abr_mar", "perdida_margen", "quiebres"],
    )
    if len(store) != 1 or store[0]["tienda_id"] != "T001":
        raise AssertionError(f"manager KPI leaked rows: {store[:3]}")
    close(store[0]["ventas_12m"], 528319.75, 0.5)
    close(store[0]["crecimiento_abr_mar"], -0.1465, 0.0005)
    close(store[0]["perdida_margen"], -5411.15, 0.5)
    close(store[0]["quiebres"], 0, 0)

    p1_manager = query_chart(
        base,
        manager_token,
        manager_by_name["P1 · ¿Qué productos rotan más en mi tienda?"],
        ["tienda_id", "producto"],
    )
    p3_manager = query_chart(
        base, manager_token, manager_by_name["P3 · ¿Está creciendo mi tienda?"], ["channel"]
    )
    p4_manager = query_chart(
        base, manager_token, manager_by_name["P4 · Detalle de mi tienda"], ["tienda_id", "producto"]
    )
    if len(p1_manager) != 10 or any(row["tienda_id"] != "T001" for row in p1_manager):
        raise AssertionError(f"manager P1 leaked rows: {p1_manager[:3]}")
    if not p3_manager or any(row["channel"] != "T001" for row in p3_manager):
        raise AssertionError(f"manager P3 leaked rows: {p3_manager[:3]}")
    if len(p4_manager) != 3 or any(row["tienda_id"] != "T001" for row in p4_manager):
        raise AssertionError(f"manager P4 expected three T001 rows: {p4_manager[:3]}")

    p2_director = query_chart(
        base,
        director_token,
        by_name["P2 · ¿Qué tiendas se quedaron sin stock más de 3 días?"],
        ["tienda_id"],
    )
    p4_director = query_chart(
        base,
        director_token,
        by_name["P4 · ¿En qué tiendas pierden dinero?"],
        ["tienda_id", "producto"],
    )
    p3_director = query_chart(
        base, director_token, by_name["P3 · Crecimiento mensual por tienda"], ["channel"]
    )
    channels = {row["channel"] for row in p3_director}
    if len(p2_director) != 3:
        raise AssertionError(f"director P2 expected three rows: {p2_director}")
    if len(p4_director) != 120:
        raise AssertionError(f"director P4 expected 120 rows: {len(p4_director)}")
    if len(channels) != 41:
        raise AssertionError(f"director P3 expected 41 channels: {sorted(channels)}")
    print("director KPIs: 24,949,918 / +2.7% / -8.5% / 16.9% / -218,476 / 3")
    print("manager KPIs: 528,320 / -14.6% / -5,411 / 0 (T001 only)")
    print(f"manager P1 rows={len(p1_manager)} P3 rows={len(p3_manager)} P4 rows={len(p4_manager)}")
    print(f"director P2 rows={len(p2_director)} P4 rows={len(p4_director)} P3 channels=41")
    print("manager access to network dashboards and datasets: denied")
    print("Superset API data queries and RLS: PASS")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(exc.read().decode(), file=sys.stderr)
        raise
