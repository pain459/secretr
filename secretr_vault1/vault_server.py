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
        store = {} # Removing default keys at startup.
        encrypt_store(store)
    else:
        with open(ENC_FILE, "rb") as f:
            decrypted = fernet.decrypt(f.read())
            store = json.loads(decrypted.decode())
    return store

@app.route("/secret/<key>", methods=["GET"])
def get_secret(key):
    store = decrypt_store()
    if key not in store:
        return jsonify({"error": "Key not found"}), 404
    return jsonify({key: store[key]})

@app.route("/secret/<key>", methods=["POST"])
def set_secret(key):
    data = request.get_json()
    value = data.get("value")
    if not value:
        return jsonify({"error": "Missing value"}), 400
    store = decrypt_store()
    store[key] = value
    encrypt_store(store)
    return jsonify({"message": f"Secret '{key}' updated"})

@app.route("/secret/<key>", methods=["DELETE"])
def delete_secret(key):
    store = decrypt_store()
    if key not in store:
        return jsonify({"error": "Key not found"}), 404
    del store[key]
    encrypt_store(store)
    return jsonify({"message": f"Secret '{key}' deleted"})

@app.route("/secrets", methods=["GET"])
def list_secrets():
    store = decrypt_store()
    return jsonify({"keys": list(store.keys())})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8200)
