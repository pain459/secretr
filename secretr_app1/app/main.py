import logging
from fastapi import FastAPI, HTTPException
from cachetools import TTLCache
import psycopg2
import requests
import os
from datetime import datetime
import time

app = FastAPI()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/var/log/app.log"),
        logging.StreamHandler()  # stream the logs in stdout
    ]
)

# CONSTANTS
VAULT_URL = os.getenv("VAULT_URL", "http://secretr_vault1:8200/secret/appuser")
DB_HOST = os.getenv("DB_HOST", "secretr_pg1")
DB_NAME = os.getenv("DB_NAME", "data_a")
DB_USER = os.getenv("DB_USER", "appuser")
last_vault_refresh_ts = 0
cooldown_secs = 10

# 30 minute cache for password (1 entry only)
password_cache = TTLCache(maxsize=1, ttl=1800)

def get_password_from_vault():
    if "password" in password_cache:
        logging.info("Using cached password.")
        return password_cache["password"]

    try:
        logging.info("Fetching password from vault: %s", VAULT_URL)
        response = requests.get(VAULT_URL, timeout=5)
        response.raise_for_status()
        password = response.json().get("appuser")
    except Exception as e:
        logging.error("Vault error: %s", str(e))
        raise RuntimeError(f"Vault unreachable or error: {e}")

    if not password or password == "null":
        logging.error("Vault returned empty or invalid password.")
        raise RuntimeError("Vault returned empty or null password")

    password_cache["appuser"] = password
    logging.info("Password cached successfully.")
    return password


def get_db_connection():
    """Create a new DB connection using cached Vault password."""
    global last_vault_refresh_ts
    try:
        password = get_password_from_vault()
        return psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=password,
            host=DB_HOST
        )
    except psycopg2.OperationalError as e:
        # Fast fail implementation
        if "password authentication failed" in str(e):
            now = time.time()
            if now - last_vault_refresh_ts > cooldown_secs:
                logging.warning("DB password failure detected. Refreshing from Vault.")
                last_vault_refresh_ts = now
                password_cache.clear()

                # Retry after clearing cache
                password = get_password_from_vault()
                return psycopg2.connect(
                    dbname=DB_NAME,
                    user=DB_USER,
                    password=password,
                    host=DB_HOST
                )
            else:
                logging.error("DB password failed but within cooldown window. Skipping vault refresh.")
        raise


@app.get("/healthz")
def health_check():
    now = datetime.utcnow().isoformat()
    logging.info(f"Manual health check success at {now}")
    return {"status": "alive"}

@app.get("/readiness")
def readiness_check():
    try:
        # Try vault first
        _ = get_password_from_vault()

        # Then try DB connection
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                _ = cur.fetchone()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Readiness failed: {str(e)}")

    return {"status": "ready"}

@app.post("/invalidate-cache")
def invalidate_cache():
    password_cache.clear()
    logging.info("Password cache invalidated.")

    try:
        password = get_password_from_vault()
        return {"message": "Password cache refreshed.", "cached": True}
    except Exception as e:
        logging.error("Failed to refresh password after cache invalidation: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Cache refresh failed: {str(e)}")


@app.get("/data")
def get_data():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name FROM demo_data")
                rows = cur.fetchall()
                logging.info("Data retrieved successfully (%d rows).", len(rows))
                return [{"id": r[0], "name": r[1]} for r in rows]
    except Exception as e:
        logging.error("Database query failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"DB query failed: {str(e)}")
