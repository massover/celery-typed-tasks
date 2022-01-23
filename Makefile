lint:
	poetry run black .

mypy:
	poetry run mypy .

cov:
	rm -f .coverage
	poetry run pytest . --cov=celery_typed_tasks
	poetry run coverage html
	open htmlcov/index.html

test:
	pytest