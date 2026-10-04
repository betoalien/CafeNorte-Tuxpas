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


KPI_RED_SQL = """
with t as (
    select channel_type, month_start, sales_mxn
    from analytics.mart_monthly_channel_type_growth
), b as (
    select min(month_start) as primero, max(month_start) as ultimo from t
)
select
    (select sum(sales_mxn) from t) as ventas_12m,
    (select max(sales_mxn) filter (where month_start = b.ultimo)
            / max(sales_mxn) filter (where month_start = b.primero) - 1
     from t where channel_type = 'FISICO') as fisico_abr_mar,
    (select max(sales_mxn) filter (where month_start = b.ultimo)
            / max(sales_mxn) filter (where month_start = b.primero) - 1
     from t where channel_type = 'ECOMMERCE') as ecommerce_abr_mar,
    (select sum(sales_mxn) filter (where channel_type = 'ECOMMERCE') / sum(sales_mxn)
     from t) as ecommerce_share,
    (select sum(gross_margin_mxn) from analytics.mart_negative_margin_products)
        as perdida_margen,
    (select count(distinct tienda_id) from analytics.mart_stockouts_over_3_days)
        as tiendas_quiebre
from b
"""

KPI_TIENDA_SQL = """
with g as (
    select min(month_start) as primero, max(month_start) as ultimo
    from analytics.mart_monthly_channel_growth
), s as (
    select c.channel as tienda_id, sum(c.sales_mxn) as ventas_12m,
           max(c.sales_mxn) filter (where c.month_start = g.ultimo)
             / nullif(max(c.sales_mxn) filter (where c.month_start = g.primero), 0) - 1
             as crecimiento_abr_mar
    from analytics.mart_monthly_channel_growth c cross join g
    where c.channel <> 'ONLINE'
    group by c.channel
), m as (
    select tienda_id, sum(gross_margin_mxn) as perdida_margen,
           count(distinct product_id) as productos_perdida
    from analytics.mart_negative_margin_products
    where tienda_id is not null
    group by tienda_id
), q as (
    select tienda_id, count(*) as quiebres
    from analytics.mart_stockouts_over_3_days
    group by tienda_id
)
select s.tienda_id, s.ventas_12m, s.crecimiento_abr_mar,
       coalesce(m.perdida_margen, 0) as perdida_margen,
       coalesce(m.productos_perdida, 0) as productos_perdida,
       coalesce(q.quiebres, 0) as quiebres
from s left join m using (tienda_id) left join q using (tienda_id)
"""

VIEWS = {
    "kpi_red": KPI_RED_SQL,
    "kpi_tienda": KPI_TIENDA_SQL,
    "v_p1_red": (
        "select right(product_id, 5) as producto, inventory_turnover_ratio as rotacion, ranking "
        "from analytics.mart_inventory_turnover_top10"
    ),
    "v_p1_tienda": (
        "select tienda_id, right(product_id, 5) as producto, "
        "inventory_turnover_ratio as rotacion, ranking "
        "from analytics.mart_inventory_turnover_by_store where ranking <= 10"
    ),
    "v_p2": (
        "select tienda_id, right(product_id, 5) as producto, "
        "to_char(start_date, 'YYYY-MM-DD') as desde, to_char(end_date, 'YYYY-MM-DD') as hasta, "
        "days as dias from analytics.mart_stockouts_over_3_days"
    ),
    "v_p3_tipo": (
        "select channel_type as canal, month_start, sales_mxn, mom_growth_pct "
        "from analytics.mart_monthly_channel_type_growth"
    ),
    "v_p3_canal": (
        "select channel, month_start, to_char(month_start, 'YYYY-MM') as mes, sales_mxn, "
        "mom_growth_pct from analytics.mart_monthly_channel_growth"
    ),
    "v_p4": (
        "select tienda_id, right(product_id, 5) as producto, units as unidades, "
        "sales_mxn as ventas_mxn, gross_margin_mxn as margen_mxn "
        "from analytics.mart_negative_margin_products where tienda_id is not null"
    ),
    "v_calidad": (
        "select source_name as fuente, sum(input_rows) as filas, "
        "sum(certified_rows) as certificadas, sum(excluded_rows) as excluidas, "
        "sum(certified_rows)::numeric / nullif(sum(input_rows), 0) as pct_certificado "
        "from analytics.mart_source_reconciliation group by source_name"
    ),
}

LABELS = {
    "tienda_id": "Tienda",
    "channel": "Canal",
    "canal": "Canal",
    "producto": "Producto",
    "rotacion": "Rotación",
    "desde": "Desde",
    "hasta": "Hasta",
    "dias": "Días",
    "mes": "Mes",
    "month_start": "Mes",
    "unidades": "Unidades",
    "ventas_mxn": "Ventas MXN",
    "margen_mxn": "Margen MXN",
    "fuente": "Fuente",
    "filas": "Filas",
    "certificadas": "Certificadas",
    "excluidas": "Excluidas",
    "pct_certificado": "% certificado",
}

MANAGER_VIEWS = {"kpi_tienda", "v_p1_tienda", "v_p2", "v_p3_canal", "v_p4"}

CHART_NAMES = set()


def virtual_dataset(database, name, sql):
    from superset import db
    from superset.connectors.sqla.models import SqlaTable

    item = (
        db.session.query(SqlaTable)
        .filter_by(database_id=database.id, table_name=name)
        .one_or_none()
    )
    if item is None:
        item = SqlaTable(database=database, schema="analytics", table_name=name)
        db.session.add(item)
    item.sql = sql.strip()
    item.is_sqllab_view = False
    db.session.flush()
    item.fetch_metadata()
    for column in item.columns:
        if column.column_name in LABELS:
            column.verbose_name = LABELS[column.column_name]
        if column.column_name == "month_start":
            column.is_dttm = True
    db.session.flush()
    return item


def metric(column, aggregate, label):
    return {
        "expressionType": "SIMPLE",
        "column": {"column_name": column},
        "aggregate": aggregate,
        "label": label,
    }


def view_chart(name, datasource, viz_type, params):
    CHART_NAMES.add(name)
    payload = {"viz_type": viz_type, "datasource": f"{datasource.id}__table", **params}
    return chart(name, datasource, viz_type, json.dumps(payload, ensure_ascii=False))


def big_number(name, datasource, column, aggregate, subheader, number_format):
    return view_chart(
        name,
        datasource,
        "big_number_total",
        {
            "metric": metric(column, aggregate, subheader),
            "subheader": subheader,
            "y_axis_format": number_format,
            "header_font_size": 0.3,
            "subheader_font_size": 0.125,
        },
    )


def bar_chart(name, datasource, column, label, number_format, descending):
    return view_chart(
        name,
        datasource,
        "dist_bar",
        {
            "groupby": ["producto"],
            "metrics": [metric(column, "SUM", label)],
            "row_limit": 10,
            "order_desc": descending,
            "show_bar_value": True,
            "show_legend": False,
            "y_axis_format": number_format,
            "x_ticks_layout": "auto",
            "bottom_margin": "auto",
        },
    )


def mom_line(name, datasource, group_column):
    return view_chart(
        name,
        datasource,
        "echarts_timeseries_line",
        {
            "x_axis": "month_start",
            "granularity_sqla": "month_start",
            "time_grain_sqla": "P1M",
            "groupby": [group_column],
            "metrics": [metric("mom_growth_pct", "MAX", "Crecimiento MoM")],
            "y_axis_format": "+.1%",
            "show_legend": True,
            "rich_tooltip": True,
            "markerEnabled": True,
            "row_limit": 1000,
        },
    )


def raw_table(name, datasource, columns, order_by, ascending, formats=None):
    return view_chart(
        name,
        datasource,
        "table",
        {
            "query_mode": "raw",
            "all_columns": columns,
            "order_by_cols": [json.dumps([order_by, ascending])],
            "row_limit": 200,
            "include_search": False,
            "column_config": {
                column: {"d3NumberFormat": number_format}
                for column, number_format in (formats or {}).items()
            },
        },
    )


def rows_layout(rows, title):
    positions = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "HEADER_ID": {"type": "HEADER", "id": "HEADER_ID", "meta": {"text": title}},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "parents": ["ROOT_ID"], "children": []},
    }
    for number, (height, items) in enumerate(rows, start=1):
        row_id = f"ROW-{number}"
        positions[row_id] = {
            "type": "ROW",
            "id": row_id,
            "parents": ["ROOT_ID", "GRID_ID"],
            "children": [],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        for item, width in items:
            node_id = f"CHART-{item.id}"
            positions[node_id] = {
                "type": "CHART",
                "id": node_id,
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID", row_id],
                "meta": {
                    "chartId": item.id,
                    "sliceName": item.slice_name,
                    "width": width,
                    "height": height,
                    "uuid": str(getattr(item, "uuid", "")),
                },
            }
            positions[row_id]["children"].append(node_id)
        positions["GRID_ID"]["children"].append(row_id)
    return positions


def publish(slug, title, role_items, rows):
    from superset import db
    from superset.models.dashboard import Dashboard

    item = db.session.query(Dashboard).filter_by(slug=slug).one_or_none()
    if item is None:
        item = Dashboard(slug=slug, published=True, position_json="{}", json_metadata="{}")
        db.session.add(item)
    item.dashboard_title = title
    item.published = True
    item.roles = role_items
    item.slices = [chart_item for _height, items in rows for chart_item, _width in items]
    positions = rows_layout(rows, title)
    item.position_json = json.dumps(positions, ensure_ascii=False)
    item.json_metadata = json.dumps(dashboard_metadata(positions), ensure_ascii=False)
    return item


def main():
    from flask import current_app
    from superset import db
    from superset.models.core import Database
    from superset.models.slice import Slice

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

        views = {name: virtual_dataset(database, name, sql) for name, sql in VIEWS.items()}

        security = current_app.appbuilder.sm
        manager_perms = set()
        for name, view in views.items():
            permission_view = security.add_permission_view_menu(
                "datasource_access", view.get_perm()
            )
            security.add_permission_role(director, permission_view)
            if name in MANAGER_VIEWS:
                security.add_permission_role(gerente, permission_view)
                manager_perms.add(view.get_perm())
        gerente.permissions = [
            permission
            for permission in gerente.permissions
            if permission.permission.name != "datasource_access"
            or permission.view_menu.name in manager_perms
        ]

        for name in ("kpi_tienda", "v_p1_tienda", "v_p2", "v_p4"):
            rls(gerente, views[name], f"gerente_t001_{name}", "tienda_id = 'T001'")
        rls(gerente, views["v_p3_canal"], "gerente_t001_v_p3_canal", "channel = 'T001'")

        red = views["kpi_red"]
        tienda = views["kpi_tienda"]
        director_rows = [
            (
                25,
                [
                    (
                        big_number(
                            "Ventas 12 meses (MXN)",
                            red,
                            "ventas_12m",
                            "MAX",
                            "Ventas 12 meses (MXN)",
                            ",.0f",
                        ),
                        3,
                    ),
                    (
                        big_number(
                            "Físico abr→mar", red, "fisico_abr_mar", "MAX", "Físico abr→mar", "+.1%"
                        ),
                        2,
                    ),
                    (
                        big_number(
                            "E-commerce abr→mar",
                            red,
                            "ecommerce_abr_mar",
                            "MAX",
                            "E-commerce abr→mar",
                            "+.1%",
                        ),
                        2,
                    ),
                    (
                        big_number(
                            "E-commerce % de ventas",
                            red,
                            "ecommerce_share",
                            "MAX",
                            "E-commerce % de ventas",
                            ".1%",
                        ),
                        2,
                    ),
                    (
                        big_number(
                            "Pérdida por margen negativo (MXN)",
                            red,
                            "perdida_margen",
                            "MAX",
                            "Pérdida por margen negativo (MXN)",
                            ",.0f",
                        ),
                        3,
                    ),
                ],
            ),
            (
                55,
                [
                    (
                        mom_line(
                            "P3 · ¿Crece el negocio y por qué canal?", views["v_p3_tipo"], "canal"
                        ),
                        12,
                    ),
                ],
            ),
            (
                70,
                [
                    (
                        view_chart(
                            "P3 · Crecimiento mensual por tienda",
                            views["v_p3_canal"],
                            "pivot_table_v2",
                            {
                                "groupbyRows": ["channel"],
                                "groupbyColumns": ["mes"],
                                "metrics": [metric("mom_growth_pct", "MAX", "MoM")],
                                "valueFormat": "+.1%",
                                "aggregateFunction": "Maximum",
                                "rowTotals": False,
                                "colTotals": False,
                                "row_limit": 1000,
                            },
                        ),
                        12,
                    ),
                ],
            ),
            (
                55,
                [
                    (
                        bar_chart(
                            "P1 · ¿Qué productos rotan más en la red?",
                            views["v_p1_red"],
                            "rotacion",
                            "Rotación",
                            ".2f",
                            True,
                        ),
                        12,
                    ),
                ],
            ),
            (
                55,
                [
                    (
                        bar_chart(
                            "P4 · ¿Qué productos pierden dinero?",
                            views["v_p4"],
                            "margen_mxn",
                            "Margen MXN",
                            ",.0f",
                            False,
                        ),
                        6,
                    ),
                    (
                        raw_table(
                            "P4 · ¿En qué tiendas pierden dinero?",
                            views["v_p4"],
                            ["producto", "tienda_id", "unidades", "ventas_mxn", "margen_mxn"],
                            "margen_mxn",
                            True,
                            {"ventas_mxn": ",.2f", "margen_mxn": ",.2f"},
                        ),
                        6,
                    ),
                ],
            ),
            (
                40,
                [
                    (
                        big_number(
                            "P2 · Tiendas con quiebres > 3 días",
                            red,
                            "tiendas_quiebre",
                            "MAX",
                            "Tiendas con quiebres > 3 días (ene a mar 2026)",
                            ",d",
                        ),
                        4,
                    ),
                    (
                        raw_table(
                            "P2 · ¿Qué tiendas se quedaron sin stock más de 3 días?",
                            views["v_p2"],
                            ["tienda_id", "producto", "desde", "hasta", "dias"],
                            "desde",
                            True,
                        ),
                        8,
                    ),
                ],
            ),
        ]
        store_rows = [
            (
                25,
                [
                    (
                        big_number(
                            "Mi tienda · Ventas 12 meses (MXN)",
                            tienda,
                            "ventas_12m",
                            "SUM",
                            "Ventas 12 meses (MXN)",
                            ",.0f",
                        ),
                        3,
                    ),
                    (
                        big_number(
                            "Mi tienda · Crecimiento abr→mar",
                            tienda,
                            "crecimiento_abr_mar",
                            "MAX",
                            "Crecimiento abr→mar",
                            "+.1%",
                        ),
                        3,
                    ),
                    (
                        big_number(
                            "Mi tienda · Pérdida por margen negativo",
                            tienda,
                            "perdida_margen",
                            "SUM",
                            "Pérdida por margen negativo (MXN)",
                            ",.0f",
                        ),
                        3,
                    ),
                    (
                        big_number(
                            "Mi tienda · Quiebres > 3 días",
                            tienda,
                            "quiebres",
                            "SUM",
                            "Quiebres > 3 días en mi tienda (ene a mar 2026)",
                            ",d",
                        ),
                        3,
                    ),
                ],
            ),
            (
                55,
                [
                    (
                        mom_line("P3 · ¿Está creciendo mi tienda?", views["v_p3_canal"], "channel"),
                        12,
                    ),
                ],
            ),
            (
                55,
                [
                    (
                        bar_chart(
                            "P1 · ¿Qué productos rotan más en mi tienda?",
                            views["v_p1_tienda"],
                            "rotacion",
                            "Rotación",
                            ".2f",
                            True,
                        ),
                        12,
                    ),
                ],
            ),
            (
                50,
                [
                    (
                        bar_chart(
                            "P4 · ¿Qué productos me hacen perder dinero?",
                            views["v_p4"],
                            "margen_mxn",
                            "Margen MXN",
                            ",.0f",
                            False,
                        ),
                        6,
                    ),
                    (
                        raw_table(
                            "P4 · Detalle de mi tienda",
                            views["v_p4"],
                            ["producto", "unidades", "ventas_mxn", "margen_mxn"],
                            "margen_mxn",
                            True,
                            {"ventas_mxn": ",.2f", "margen_mxn": ",.2f"},
                        ),
                        6,
                    ),
                ],
            ),
        ]
        quality_rows = [
            (
                30,
                [
                    (
                        raw_table(
                            "Calidad · Conciliación por fuente",
                            views["v_calidad"],
                            ["fuente", "filas", "certificadas", "excluidas", "pct_certificado"],
                            "fuente",
                            True,
                            {
                                "filas": ",d",
                                "certificadas": ",d",
                                "excluidas": ",d",
                                "pct_certificado": ".1%",
                            },
                        ),
                        12,
                    ),
                ],
            ),
        ]
        publish("cafenorte-4-respuestas", "CaféNorte — Dirección", [director], director_rows)
        publish("cafenorte-mi-tienda", "CaféNorte — Mi tienda", [gerente], store_rows)
        publish("cafenorte-calidad-datos", "CaféNorte — Calidad de datos", [director], quality_rows)

        for stale in db.session.query(Slice).all():
            if stale.slice_name not in CHART_NAMES:
                stale.dashboards = []
                db.session.delete(stale)
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
