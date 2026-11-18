from alembic import context
from app.database import engine, Base
from app import models  # noqa: F401 - register model metadata for Alembic

config = context.config
if context.is_offline_mode():
    context.configure(
        url=str(engine.url),
        target_metadata=Base.metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()

        if engine.dialect.name == "sqlite":
            violations = connection.exec_driver_sql(
                "PRAGMA foreign_key_check"
            ).fetchall()
            if violations:
                raise RuntimeError("Foreign key validation failed")
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
