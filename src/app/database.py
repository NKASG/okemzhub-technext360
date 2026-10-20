import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# True when running inside Cloudflare Python Workers (Pyodide / WebAssembly).
IS_WORKERS = sys.platform == "emscripten"

# Sessions are bound to an engine by init_engine(). Locally that happens at
# import time; on Cloudflare Workers it happens on the first request, once the
# Hyperdrive binding (database credentials) is available.
SessionLocal = sessionmaker(autocommit=False, autoflush=False)
engine = None


def init_engine(url, **engine_kwargs):
    """Create the global engine and bind SessionLocal to it."""
    global engine
    # check_same_thread is SQLite-only; ignored for other databases
    connect_args = {"check_same_thread": False} if str(url).startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, **engine_kwargs)
    SessionLocal.configure(bind=engine)
    return engine


if not IS_WORKERS:
    init_engine(settings.DATABASE_URL)


class Base(DeclarativeBase):
    pass
