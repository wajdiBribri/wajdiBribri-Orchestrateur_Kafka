FROM python:3.11-slim

WORKDIR /app

# Installer uv
RUN pip install --no-cache-dir uv

# Copier pyproject.toml et README (utile pour PEP 621)
COPY pyproject.toml README.md ./

# Installer les dépendances
RUN uv pip install --system --no-cache .

# Copier le code de l’app
COPY orchestrator /app/orchestrator
COPY Objets.json /app/Objets.json

# Variables d’environnement
ENV OBJETS_PATH=/app/Objets.json

# Lancer FastAPI
CMD ["uvicorn", "orchestrator.app:app", "--host", "0.0.0.0", "--port", "8000"]
