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
        db.session.commit()


def main():
    from superset import db
    from superset.models.dashboard import Dashboard

    with current_app.app_context():
        director = role("director")
        gerente = role("gerente_t001")
        gamma = current_app.appbuilder.sm.find_role("Gamma")
        alpha = current_app.appbuilder.sm.find_role("Alpha")
        user("admin", os.environ["SUPERSET_ADMIN_PASSWORD"], [role("Admin")])
        user("director", os.environ["SUPERSET_ADMIN_PASSWORD"], [role("Admin"), director])
        user("gerente_t001", os.environ["GERENTE_T001_PASSWORD"], [alpha, gamma, gerente])

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
        db.session.commit()


if __name__ == "__main__":
    from superset.app import create_app

    app = create_app()
    with app.app_context():
        main()
