from fastapi import FastAPI, HTTPException
from cachetools import TTLCache
import psycopg2
import requests
import os

app = FastAPI()

# CONSTANTS
VAULT_URL = os.getenv("VAULT_URL", "http://secretr_vault1:8200/secret/appuser")
DB_HOST = os.getenv("DB_HOST", "secretr_pg1")
DB_NAME = os.getenv("DB_NAME", "data_a")
DB_USER = os.getenv("DB_USER", "appuser")

# 30 minute cache for password (1 entry only)
password_cache = TTLCache(maxsize=1, ttl=1800)

def get_password_from_vault():
    """Get and cache the database password from Vault."""
    if "password" in password_cache:
        return password_cache["password"]

    try:
        response = requests.get(VAULT_URL, timeout=5)
        response.raise_for_status()
        password = response.json().get("appuser")
    except Exception as e:
        raise RuntimeError(f"Vault unreachable or error: {e}")

    if not password or password == "null":
        raise RuntimeError("Vault returned empty or null password")

    password_cache["appuser"] = password
    return password

def get_db_connection():
    """Create a new DB connection using cached Vault password."""
    password = get_password_from_vault()
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=password,
        host=DB_HOST
    )

@app.get("/healthz")
def health_check():
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

@app.get("/data")
def get_data():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name FROM demo_data")
                rows = cur.fetchall()
                return [{"id": r[0], "name": r[1]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB query failed: {str(e)}")