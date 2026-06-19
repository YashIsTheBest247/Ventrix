from sqlmodel import Session, SQLModel, create_engine

from .config import settings

# Normalize the URL: Render/Heroku hand out "postgres://" which SQLAlchemy 2.x
# no longer accepts — it wants "postgresql://".
db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

is_sqlite = db_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine = create_engine(
    db_url,
    echo=False,
    connect_args=connect_args,
    # pool_pre_ping avoids "server closed the connection" on idle cloud Postgres.
    pool_pre_ping=not is_sqlite,
)


def init_db() -> None:
    # Import models so SQLModel registers the tables before create_all.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _ensure_columns()


def _ensure_columns() -> None:
    """Lightweight migration: add columns that create_all can't add to tables
    that already exist (create_all only creates missing tables). Lets schema
    changes like the per-user `user_id` roll out without dropping the DB.
    Old rows get NULL user_id (owned by nobody → hidden), new rows are scoped."""
    from sqlalchemy import inspect, text

    wanted = {
        "registration": [("user_id", "INTEGER")],
        "note": [("user_id", "INTEGER")],
        "stickyitem": [("user_id", "INTEGER")],
        "notificationlog": [("user_id", "INTEGER")],
    }
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    for table, cols in wanted.items():
        if table not in tables:
            continue
        have = {c["name"] for c in insp.get_columns(table)}
        for name, coltype in cols:
            if name not in have:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {coltype}"))


def get_session():
    with Session(engine) as session:
        yield session
