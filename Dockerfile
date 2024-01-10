FROM python:3.12.1-slim-bullseye
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /djangoapp

COPY requirements.txt .

RUN apt-get update && apt-get install -y nano && \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    adduser --disabled-password --no-create-home duser

COPY . .

RUN chown -R duser:duser /djangoapp

COPY entrypoint.sh ./scripts/entrypoint.sh
RUN chmod +x /djangoapp/scripts/entrypoint.sh

USER duser

EXPOSE 8000
