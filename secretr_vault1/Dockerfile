FROM python:3.10-slim

WORKDIR /vault

COPY vault_server.py .
COPY vault.key .

RUN pip install flask cryptography

EXPOSE 8200

CMD ["python", "vault_server.py"]
