from flask import Flask, request, jsonify
from cryptography.fernet import Fernet
import os
import json

app = Flask(__name__)

KEY_FILE = "vault.key"
ENC_FILE = "data/store.enc"

# Load or fail fast
if not os.path.exists(KEY_FILE):
    raise RuntimeError("Missing vault.key file. Please generate one using Fernet.")

with open(KEY_FILE, "rb") as f:
    fernet = Fernet(f.read())

def encrypt_store(data: dict):
    payload = json.dumps(data).encode()
    encrypted = fernet.encrypt(payload)
    with open(ENC_FILE, "wb") as f:
        f.write(encrypted)

def decrypt_store() -> dict:
    if not os.path.exists(ENC_FILE):
        password = Fernet.generate_key().decode()
        store = {"postgres": password}
        encrypt_store(store)
    else:
        with open(ENC_FILE, "rb") as f:
            decrypted = fernet.decrypt(f.read())
            store = json.loads(decrypted.decode())
    return store

@app.route("/secret/postgres", methods=["GET"])
def get_password():
    store = decrypt_store()
    return jsonify({"password": store["postgres"]})

@app.route("/secret/postgres", methods=["POST"])
def update_password():
    data = request.get_json()
    password = data.get("password")
    if not password:
        return jsonify({"error": "Missing password"}), 400
    store = decrypt_store()
    store["postgres"] = password
    encrypt_store(store)
    return jsonify({"message": "Password updated"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8200)
