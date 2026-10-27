"""Cloudflare Python Workers entry point.

Runs the FastAPI app through the Workers ASGI adapter. The database is reached
through the HYPERDRIVE binding and the JWT secret comes from the SECRET_KEY
Worker secret (see wrangler.jsonc and the README).
"""

from sqlalchemy import URL
from sqlalchemy.pool import NullPool
from workers import WorkerEntrypoint, asgi

from app import database
from app.core.config import settings
from app.main import app

_configured = False


def _configure(env) -> None:
    """Bind the database engine and secrets on the first request."""
    global _configured
    if _configured:
        return

    hd = env.HYPERDRIVE
    url = URL.create(
        "postgresql+pg8000",
        username=hd.user,
        password=hd.password,
        host=hd.host,
        port=int(hd.port),
        database=hd.database,
    )
    # Workers cannot reuse a socket across requests, and Hyperdrive already
    # pools connections, so SQLAlchemy should not keep its own pool.
    # Hyperdrive already encrypts the connection to the database, and the
    # Workers runtime does not allow upgrading this socket to TLS, so pg8000
    # must not try (it otherwise attempts SSL whenever the server offers it).
    database.init_engine(url, poolclass=NullPool, connect_args={"ssl_context": False})

    secret = getattr(env, "SECRET_KEY", None)
    if secret:
        settings.SECRET_KEY = str(secret)

    _configured = True


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        _configure(self.env)
        return await asgi.fetch(app, request, self.env)
