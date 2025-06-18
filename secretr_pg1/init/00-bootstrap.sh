#!/bin/bash
set -e

echo "[INFO] Waiting for Vault to become available..."

until curl -s http://secretr_vault1:8200/secret/admin >/dev/null; do
  sleep 1
done

echo "[INFO] Fetching admin password from vault..."
ADMIN_PASS=$(curl -s http://secretr_vault1:8200/secret/admin | jq -r .admin)  #TO-DO: remove the most generic name for user.

if [ -z "$ADMIN_PASS" ] || [ "$ADMIN_PASS" = "null" ]; then
  echo "[ERROR] Admin password is empty or not found in vault."
  exit 1
fi

echo "[INFO] Setting admin password and creating databases..."

#TO-DO: Remove the prerequisite step of creating databases at the start.

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  ALTER USER $POSTGRES_USER WITH PASSWORD '${ADMIN_PASS}';
  CREATE DATABASE data_a;
  CREATE DATABASE data_b;
EOSQL
