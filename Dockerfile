FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependências em layer separada para aproveitar cache
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "tuxo.main:app", "--host", "0.0.0.0", "--port", "8080"]
