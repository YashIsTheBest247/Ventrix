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


def get_session():
    with Session(engine) as session:
        yield session
