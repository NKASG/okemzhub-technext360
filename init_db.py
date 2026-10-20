"""
Create tables, add missing columns and seed the default businesses.

Run this once from your own machine against the production database before
deploying (and again whenever models change), because the Cloudflare Worker
does not run this setup at startup:

    DATABASE_URL="postgresql://..." python init_db.py
"""


import pathlib as _pathlib, sys as _sys
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parent / "src"))  # app lives in src/
from app.main import init_database

if __name__ == "__main__":
    init_database()
    print("Database is ready.")
