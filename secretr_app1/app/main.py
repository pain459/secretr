from fastapi import FastAPI, HTTPException
import psycopg2
import requests
import os

VAULT_URL = os.getenv("VAULT_URL", "http://secretr_vault1:8200/secret/appuser")
DB_HOST = os.getenv("DB_HOST", "secretr_pg1")
DB_NAME = os.getenv("DB_NAME", "data_a")
DB_USER = os.getenv("DB_USER", "appuser")

# Attempt to fetch password from vault
response = requests.get(VAULT_URL)
if response.status_code != 200:
    raise RuntimeError("Failed to fetch password from vault")

password = response.json().get("appuser")
if not password or password == "null":
    raise RuntimeError("Vault did not return a valid password")

# Attempt to connect to PostgreSQL
try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=password,
        host=DB_HOST
    )
except Exception as e:
    raise RuntimeError(f"Database connection failed: {e}")

app = FastAPI()

@app.get("/data")
def get_data():
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM demo_data")
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1]} for r in rows]
