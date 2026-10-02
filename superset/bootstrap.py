import os

from flask import current_app


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


def chart(name, datasource, viz_type, params):
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
        item = RowLevelSecurityFilter(name=name, group_key=role_item.name, clause=clause, filter_type="Regular")
        db.session.add(item)
    item.clause = clause
    item.filter_type = "Regular"
    item.roles = [role_item]
    item.tables = [table_item]


def main():
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

        database = db.session.query(Database).filter_by(database_name="CafeNorte analytics").one_or_none()
        if database is None:
            database = Database(database_name="CafeNorte analytics", sqlalchemy_uri=os.environ["SUPERSET_ANALYTICS_DB"])
            db.session.add(database)
            db.session.flush()
        database.sqlalchemy_uri = os.environ["SUPERSET_ANALYTICS_DB"]

        tables = {
            name: dataset(database, name)
            for name in (
                "mart_inventory_turnover_top10",
                "mart_stockouts_over_3_days",
                "mart_monthly_channel_growth",
                "mart_negative_margin_products",
                "mart_source_reconciliation",
            )
        }
        security = current_app.appbuilder.sm
        for table in tables.values():
            permission_view = security.add_permission_view_menu("datasource_access", table.get_perm())
            security.add_permission_role(director, permission_view)
            security.add_permission_role(gerente, permission_view)
        charts = [
            chart("P1 · Rotación top 10", tables["mart_inventory_turnover_top10"], "bar", '{"groupby": ["product_id"], "metrics": ["inventory_turnover_ratio"], "row_limit": 10}'),
            chart("P2 · Stockouts > 3 días", tables["mart_stockouts_over_3_days"], "table", '{"all_columns": ["tienda_id", "product_id", "start_date", "end_date", "days"]}'),
            chart("P3 · Crecimiento por canal", tables["mart_monthly_channel_growth"], "echarts_timeseries", '{"groupby": ["month_start", "channel"], "metrics": ["sales_mxn"]}'),
            chart("P4 · Margen negativo", tables["mart_negative_margin_products"], "table", '{"all_columns": ["product_id", "tienda_id", "units", "sales_mxn", "gross_margin_mxn"]}'),
            chart("Reconciliación de fuentes", tables["mart_source_reconciliation"], "table", '{"all_columns": ["source_name", "period", "product_id", "input_rows", "certified_rows", "excluded_rows"]}'),
        ]
        rls(gerente, tables["mart_stockouts_over_3_days"], "gerente_t001_p2", "tienda_id = 'T001'")
        rls(gerente, tables["mart_negative_margin_products"], "gerente_t001_p4", "tienda_id = 'T001'")
        rls(gerente, tables["mart_monthly_channel_growth"], "gerente_t001_p3", "channel = 'T001'")

        dashboard = db.session.query(Dashboard).filter_by(slug="cafenorte-4-respuestas").one_or_none()
        if dashboard is None:
            dashboard = Dashboard(
                dashboard_title="CaféNorte — 4 respuestas",
                slug="cafenorte-4-respuestas",
                published=True,
                position_json="{}",
                json_metadata="{}",
            )
            db.session.add(dashboard)
        dashboard.roles = [director, gerente]
        dashboard.slices = charts
        dashboard.position_json = "{" + ",".join(f'\"CHART-{item.id}\": {{\"meta\": {{\"sliceName\": \"{item.slice_name}\"}}}}' for item in charts) + "}"
        db.session.commit()


if __name__ == "__main__":
    from superset.app import create_app

    app = create_app()
    with app.app_context():
        main()
