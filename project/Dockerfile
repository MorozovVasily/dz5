FROM python:3.8-slim

RUN mkdir -p /app/project
COPY requirements.txt /app/
WORKDIR /app

RUN pip install -r requirements.txt

COPY . project/
ENV FLASK_APP=project

ENTRYPOINT flask run --host=0.0.0.0