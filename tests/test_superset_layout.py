import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("superset_bootstrap", ROOT / "superset/bootstrap.py")
assert SPEC and SPEC.loader
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


def test_dashboard_layout_has_consistent_nodes() -> None:
    charts = [
        SimpleNamespace(id=index, slice_name=f"Chart {index}", uuid=f"uuid-{index}")
        for index in range(6)
    ]
    positions = bootstrap.dashboard_layout(charts)
    assert positions["ROOT_ID"]["children"] == ["GRID_ID"]
    assert positions["GRID_ID"]["children"] == ["ROW-1", "ROW-2", "ROW-3"]
    for _node_id, node in positions.items():
        if not isinstance(node, dict):
            continue
        for child_id in node.get("children", []):
            assert child_id in positions
        for parent_id in node.get("parents", []):
            assert parent_id in positions
    assert [positions[f"CHART-{index}"]["meta"]["chartId"] for index in range(6)] == list(range(6))
