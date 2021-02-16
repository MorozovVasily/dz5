#!/bin/bash

sudo apt-get update && sudo apt-get install -y python3-pip docker-ce

sudo docker run --name docker-postgres --net=host -e POSTGRES_PASSWORD=qp1337 -d postgres

pip3 install -r project/requirements.txt

export FLASK_APP=project
export FLASK_DEBUG=1

flask run --host=0.0.0.0

