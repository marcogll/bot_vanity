# Vanessa Bot Vanity

Backend FastAPI para procesar webhooks de Evolution API y responder como Vanessa,
asistente virtual de Vanity Nail Salon.

## Setup local en Arch/Omarchy

No instales dependencias con `pip` global. Arch marca Python como entorno
administrado externamente, por lo que debes usar un virtualenv del proyecto:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Si no activas el virtualenv, ejecuta los binarios directamente:

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

## Variables de entorno

Crea un `.env` basado en `.env.example`.

Genera una clave válida para cifrado:

```bash
.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Coloca el resultado en `AES_ENCRYPTION_KEY`.

## Ejecutar

Levanta PostgreSQL local:

```bash
docker compose up -d vanessa-db
```

Con el `.env` configurado:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8001
```

Healthcheck:

```bash
curl http://127.0.0.1:8001/health
```

## Docker

Para levantar aplicación y base de datos juntos:

```bash
docker compose up -d --build
```

La app queda publicada en:

```text
http://127.0.0.1:8001
```
