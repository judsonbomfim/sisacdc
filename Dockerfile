FROM python:3.12.1-slim-bullseye
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /djangoapp

COPY requirements.txt .

RUN apt-get update && apt-get install -y nano && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

COPY entrypoint.sh .
RUN chmod +x /djangoapp/entrypoint.sh

EXPOSE 8000
