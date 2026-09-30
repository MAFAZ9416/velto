import os
from pathlib import Path

import dj_database_url
import psycopg2

env_path = Path(r"C:\Users\mafaz\OneDrive\Desktop\Velto_Conversion\backend\.env")
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

url = os.environ["DATABASE_URL"]
cfg = dj_database_url.parse(url)
conn = psycopg2.connect(
    dbname=cfg["NAME"],
    user=cfg["USER"],
    password=cfg["PASSWORD"],
    host=cfg["HOST"],
    port=cfg["PORT"],
    sslmode="require",
)
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'test_neondb';")
    cur.execute("DROP DATABASE IF EXISTS test_neondb;")
print("dropped test_neondb if present")
