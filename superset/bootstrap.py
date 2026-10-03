import json
import os


def role(name):
    from flask_appbuilder.security.sqla.models import Role
    from superset import db

    item = db.session.query(Role).filter_by(name=name).one_or_none()
    if item is None:
        item = Role(name=name)
        db.session.add(item)
        db.session.flush()
    return item


def user(username, password, roles):
    from flask import current_app
    from superset import db

    manager = current_app.appbuilder.sm
    existing = manager.find_user(username=username)
    if existing is None:
        manager.add_user(
            username=username,
            first_name=username,
            last_name="Demo",
            email=f"{username}@cafenorte.local",
            role=roles,
            password=password,
        )
    else:
        existing.roles = roles
        manager.reset_password(existing.id, password)
        db.session.commit()


def dataset(database, table_name):
    from superset import db
    from superset.connectors.sqla.models import SqlaTable

    item = (
        db.session.query(SqlaTable)
        .filter_by(database_id=database.id, schema="analytics", table_name=table_name)
        .one_or_none()
    )
    if item is None:
        item = SqlaTable(
            database=database,
            schema="analytics",
            table_name=table_name,
            is_featured=False,
            sql=None,
        )
        db.session.add(item)
        db.session.flush()
    item.fetch_metadata()
    return item


def chart(name, datasource, viz_type, params, description=None):
    from superset import db
    from superset.models.slice import Slice

    item = db.session.query(Slice).filter_by(slice_name=name).one_or_none()
    if item is None:
        item = Slice(slice_name=name, datasource_type="table")
        db.session.add(item)
    item.datasource_id = datasource.id
    item.datasource_type = "table"
    item.viz_type = viz_type
    item.params = params
    item.description = description
    item.query_context = None
    db.session.flush()
    return item


def rls(role_item, table_item, name, clause):
    from superset import db
    from superset.connectors.sqla.models import RowLevelSecurityFilter

    item = (
        db.session.query(RowLevelSecurityFilter)
        .filter_by(name=name, group_key=role_item.name)
        .one_or_none()
    )
    if item is None:
        item = RowLevelSecurityFilter(
            name=name, group_key=role_item.name, clause=clause, filter_type="Regular"
        )
        db.session.add(item)
    item.clause = clause
    item.filter_type = "Regular"
    item.roles = [role_item]
    item.tables = [table_item]


def dashboard_layout(charts, markdowns=(), title="CaféNorte"):
    positions = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "HEADER_ID": {
            "type": "HEADER",
            "id": "HEADER_ID",
            "meta": {"text": title},
        },
        "GRID_ID": {
            "type": "GRID",
            "id": "GRID_ID",
            "parents": ["ROOT_ID"],
            "children": [],
        },
    }
    items = list(markdowns) + list(charts)
    markdown_counter = 0
    for index in range(0, len(items), 2):
        row_id = f"ROW-{index // 2 + 1}"
        row = {
            "type": "ROW",
            "id": row_id,
            "parents": ["ROOT_ID", "GRID_ID"],
            "children": [],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        for item in items[index : index + 2]:
            if isinstance(item, str):
                markdown_counter += 1
                node_id = f"MARKDOWN-{markdown_counter}"
                positions[node_id] = {
                    "type": "MARKDOWN",
                    "id": node_id,
                    "children": [],
                    "parents": ["ROOT_ID", "GRID_ID", row_id],
                    "meta": {"code": item, "width": 12, "height": 20},
                }
            else:
                node_id = f"CHART-{item.id}"
                positions[node_id] = {
                    "type": "CHART",
                    "id": node_id,
                    "children": [],
                    "parents": ["ROOT_ID", "GRID_ID", row_id],
                    "meta": {
                        "chartId": item.id,
                        "sliceName": item.slice_name,
                        "width": 6,
                        "height": 50,
                        "uuid": str(getattr(item, "uuid", "")),
                    },
                }
            row["children"].append(node_id)
        positions[row_id] = row
        positions["GRID_ID"]["children"].append(row_id)
    return positions


def dashboard_metadata(positions):
    return {
        "native_filter_configuration": [],
        "color_scheme": "",
        "refresh_frequency": 0,
        "positions": positions,
        "chart_configuration": {},
        "timed_refresh_immune_slices": [],
        "expanded_slices": {},
        "label_colors": {},
        "default_filters": "{}",
    }


def main():
    from flask import current_app
    from superset import db
    from superset.models.core import Database
    from superset.models.dashboard import Dashboard

    with current_app.app_context():
        director = role("director")
        gerente = role("gerente_t001")
        gamma = current_app.appbuilder.sm.find_role("Gamma")
        alpha = current_app.appbuilder.sm.find_role("Alpha")
        user("admin", os.environ["SUPERSET_ADMIN_PASSWORD"], [role("Admin")])
        user("director", os.environ["DIRECTOR_PASSWORD"], [alpha, director])
        user("gerente_t001", os.environ["GERENTE_T001_PASSWORD"], [gamma, gerente])

        database = (
            db.session.query(Database).filter_by(database_name="CafeNorte analytics").one_or_none()
        )
        if database is None:
            database = Database(
                database_name="CafeNorte analytics",
                sqlalchemy_uri=os.environ["SUPERSET_ANALYTICS_DB"],
            )
            db.session.add(database)
            db.session.flush()
        database.sqlalchemy_uri = os.environ["SUPERSET_ANALYTICS_DB"]

        tables = {
            name: dataset(database, name)
            for name in (
                "mart_inventory_turnover_top10",
                "mart_inventory_turnover_by_store",
                "mart_stockouts_over_3_days",
                "mart_monthly_channel_growth",
                "mart_monthly_channel_type_growth",
                "mart_negative_margin_products",
                "mart_source_reconciliation",
            )
        }
        security = current_app.appbuilder.sm
        manager_table_names = {
            "mart_inventory_turnover_by_store",
            "mart_stockouts_over_3_days",
            "mart_monthly_channel_growth",
            "mart_negative_margin_products",
        }
        for table_name, table in tables.items():
            permission_view = security.add_permission_view_menu(
                "datasource_access", table.get_perm()
            )
            security.add_permission_role(director, permission_view)
            if table_name in manager_table_names:
                security.add_permission_role(gerente, permission_view)
        gerente.permissions = [
            permission
            for permission in gerente.permissions
            if permission.permission.name != "datasource_access"
            or permission.view_menu.name
            in {
                tables[name].get_perm()
                for name in manager_table_names
            }
        ]
        charts = [
            chart(
                "P1 · Rotación top 10",
                tables["mart_inventory_turnover_top10"],
                "table",
                '{"all_columns": ["product_id", "units_sold", '
                '"average_valid_inventory_units", "inventory_turnover_ratio", "ranking"]}',
            ),
            chart(
                "P2 · Stockouts > 3 días",
                tables["mart_stockouts_over_3_days"],
                "table",
                '{"all_columns": ["tienda_id", "product_id", "start_date", "end_date", "days"]}',
                "Sin filas para esta tienda significa que no tuvo stockouts de más de 3 días "
                "consecutivos en el periodo.",
            ),
            chart(
                "P3 · Crecimiento por canal",
                tables["mart_monthly_channel_growth"],
                "echarts_timeseries_line",
                '{"granularity_sqla": "month_start", "time_grain_sqla": "P1M", '
                '"groupby": ["channel"], "metrics": '
                '[{"expressionType": "SIMPLE", "column": {"column_name": "mom_growth_pct"}, '
                '"aggregate": "AVG", "label": "Crecimiento %"}]}',
            ),
            chart(
                "P3 · Físico vs e-commerce",
                tables["mart_monthly_channel_type_growth"],
                "pivot_table_v2",
                '{"granularity_sqla": "month_start", "time_grain_sqla": "P1M", '
                '"groupby": ["channel_type"], "metrics": '
                '[{"expressionType": "SIMPLE", "column": {"column_name": "mom_growth_pct"}, '
                '"aggregate": "AVG", "label": "Crecimiento %"}]}',
            ),
            chart(
                "P4 · Margen negativo",
                tables["mart_negative_margin_products"],
                "pivot_table_v2",
                '{"groupby": ["product_id"], "metrics": [{"expressionType": "SIMPLE", '
                '"column": {"column_name": "gross_margin_mxn"}, "aggregate": "SUM", '
                '"label": "Margen MXN"}], "order_desc": false}',
            ),
            chart(
                "Reconciliación de fuentes",
                tables["mart_source_reconciliation"],
                "table",
                '{"all_columns": ["source_name", "period", "product_id", "input_rows", '
                '"certified_rows", "excluded_rows"]}',
            ),
        ]
        store_p1 = chart(
            "P1 · Rotación mi tienda",
            tables["mart_inventory_turnover_by_store"],
            "table",
            '{"all_columns": ["product_id", "units_sold", '
            '"average_valid_inventory_units", "inventory_turnover_ratio", "ranking"]}',
        )
        p2_total = chart(
            "P2 · Tiendas con quiebres > 3 días",
            tables["mart_stockouts_over_3_days"],
            "big_number_total",
            '{"metric": {"expressionType": "SIMPLE", "column": '
            '{"column_name": "tienda_id"}, "aggregate": "COUNT_DISTINCT", '
            '"label": "Tiendas con quiebres > 3 días"}, '
            '"subheader": "Sin quiebres de más de 3 días en el periodo"}',
        )
        p4_total = chart(
            "P4 · Tiendas afectadas",
            tables["mart_negative_margin_products"],
            "big_number_total",
            '{"metric": {"expressionType": "SIMPLE", "column": '
            '{"column_name": "tienda_id"}, "aggregate": "COUNT_DISTINCT", '
            '"label": "Tiendas afectadas"}}',
        )
        p4_detail = chart(
            "P4 · Detalle de margen negativo",
            tables["mart_negative_margin_products"],
            "table",
            '{"all_columns": ["product_id", "tienda_id", "units", "sales_mxn", '
            '"gross_margin_mxn"]}',
        )
        p3_physical = chart(
            "P3 · Físico abr→mar",
            tables["mart_monthly_channel_type_growth"],
            "table",
            '{"all_columns": ["channel_type", "month_start", "mom_growth_pct"]}',
            '',
        )
        p3_ecommerce = chart(
            "P3 · E-commerce abr→mar",
            tables["mart_monthly_channel_type_growth"],
            "table",
            '{"all_columns": ["channel_type", "month_start", "mom_growth_pct"]}',
            '',
        )
        p3_share = chart(
            "P3 · E-commerce % de ventas",
            tables["mart_monthly_channel_type_growth"],
            "table",
            '{"all_columns": ["channel_type", "month_start", "sales_mxn"]}',
            '',
        )
        rls(gerente, tables["mart_stockouts_over_3_days"], "gerente_t001_p2", "tienda_id = 'T001'")
        rls(
            gerente,
            tables["mart_negative_margin_products"],
            "gerente_t001_p4",
            "tienda_id = 'T001'",
        )
        rls(gerente, tables["mart_monthly_channel_growth"], "gerente_t001_p3", "channel = 'T001'")
        rls(
            gerente,
            tables["mart_inventory_turnover_by_store"],
            "gerente_t001_p1",
            "tienda_id = 'T001'",
        )

        dashboard = (
            db.session.query(Dashboard).filter_by(slug="cafenorte-4-respuestas").one_or_none()
        )
        if dashboard is None:
            dashboard = Dashboard(
                dashboard_title="CaféNorte — 4 respuestas",
                slug="cafenorte-4-respuestas",
                published=True,
                position_json="{}",
                json_metadata="{}",
            )
            db.session.add(dashboard)
        dashboard.roles = [director]
        dashboard.dashboard_title = "CaféNorte — Dirección"
        dashboard.slices = [
            *charts[:-1], p2_total, p4_total, p3_physical, p3_ecommerce, p3_share
        ]
        positions = dashboard_layout(
            dashboard.slices,
            title="CaféNorte — Dirección",
        )
        dashboard.position_json = json.dumps(positions, ensure_ascii=False)
        dashboard.json_metadata = json.dumps(
            dashboard_metadata(positions), ensure_ascii=False
        )
        store_dashboard = (
            db.session.query(Dashboard).filter_by(slug="cafenorte-mi-tienda").one_or_none()
        )
        if store_dashboard is None:
            store_dashboard = Dashboard(
                dashboard_title="CaféNorte — Mi tienda",
                slug="cafenorte-mi-tienda",
                published=True,
                position_json="{}",
                json_metadata="{}",
            )
            db.session.add(store_dashboard)
        store_dashboard.roles = [gerente]
        store_dashboard.dashboard_title = "CaféNorte — Mi tienda"
        store_dashboard.slices = [store_p1, p2_total, charts[1], charts[2], p4_total, p4_detail]
        store_positions = dashboard_layout(
            store_dashboard.slices,
            title="CaféNorte — Mi tienda",
        )
        store_dashboard.position_json = json.dumps(store_positions, ensure_ascii=False)
        store_dashboard.json_metadata = json.dumps(
            dashboard_metadata(store_positions), ensure_ascii=False
        )
        quality_dashboard = (
            db.session.query(Dashboard).filter_by(slug="cafenorte-calidad-datos").one_or_none()
        )
        if quality_dashboard is None:
            quality_dashboard = Dashboard(
                dashboard_title="CaféNorte — Calidad de datos",
                slug="cafenorte-calidad-datos",
                published=True,
                position_json="{}",
                json_metadata="{}",
            )
            db.session.add(quality_dashboard)
        quality_dashboard.roles = [director]
        quality_dashboard.slices = [charts[-1]]
        quality_positions = dashboard_layout(
            [charts[-1]],
            title="CaféNorte — Calidad de datos",
        )
        quality_dashboard.position_json = json.dumps(quality_positions, ensure_ascii=False)
        quality_dashboard.json_metadata = json.dumps(
            dashboard_metadata(quality_positions), ensure_ascii=False
        )
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            raise RuntimeError(
                "No se pudo guardar la metadata de Superset "
                f"({exc.__class__.__name__}: {exc}); una SECRET_KEY distinta "
                "es una causa posible. Si aplica, ejecuta "
                "`uv run cafenorte reset --yes`"
            ) from exc


if __name__ == "__main__":
    from superset.app import create_app

    app = create_app()
    with app.app_context():
        main()
