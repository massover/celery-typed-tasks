lint:
	poetry run isort .
	poetry run black .

mypy:
	poetry run mypy .

covci:
	rm -f .coverage
	poetry run pytest tests --cov=celery_typed_tasks --cov-branch --cov-report xml

cov:
	rm -f .coverage
	poetry run pytest tests --cov=celery_typed_tasks --cov-branch --cov-report html
	open htmlcov/index.html

test:
	poetry run pytest