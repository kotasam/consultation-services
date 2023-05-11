SHELL := /bin/bash

env-setup:
	rm -rf venv
	python3.8 -m venv venv; \
	source venv/bin/activate; \
	pip install -r requirements.txt

run-local:
	source venv/bin/activate; \
	export CONFIG_PATH=configs/local.cfg; \
	python manage.py makemigrations; \
	python manage.py migrate; \
	black .; \
	python manage.py runserver

run-dev:
	conda deactivate; \
	conda activate consultation; \
	pip install -r requirements.txt; \
	export CONFIG_PATH=configs/dev.cfg; \
	python manage.py makemigrations; \
	python manage.py migrate; \
	rm -rf worke_consultation_service/static; \
	python manage.py collectstatic; \
	sudo systemctl restart consultation

run-stage:
	conda deactivate; \
	conda activate consultation; \
	pip install -r requirements.txt; \
	export CONFIG_PATH=configs/stage.cfg; \
	python manage.py makemigrations; \
	python manage.py migrate; \
	rm -rf worke_consultation_service/static; \
	python manage.py collectstatic; \
	sudo systemctl restart consultation

run-grpc-local:
	source venv/bin/activate
	export CONFIG_PATH=configs/local.cfg; \
	python grpc_server.py

run-grpc-dev:
	source venv/bin/activate
	export CONFIG_PATH=configs/dev.cfg; \
	python grpc_server.py
