install-poetry:
	pip install pipx
	pipx ensurepath
	pipx install poetry

install-deps:
	poetry install --no-root

format:
	poetry run black src --line-length 80
	poetry run isort src

run-app:
	cd src && poetry run python main.py

build_container:
	docker build -t telegram_bot .

run_container:
	 docker run --env-file ./.env -d telegram_bot

