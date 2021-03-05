FROM python:3.8-slim

RUN mkdir -p /app/project
COPY requirements.txt /app/
WORKDIR /app

RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y wget

COPY . project/
ENV FLASK_APP=project

COPY .aws /root/.aws

ENTRYPOINT flask run --host=0.0.0.0
