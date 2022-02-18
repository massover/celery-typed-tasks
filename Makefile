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

patch:
	poetry version patch

bump: patch
	echo "\"\"\"\"This file is generated on bump. \"\"\"\n__version__ = \"$(shell poetry version | tail -c +20)\"" > celery_typed_tasks/_version.py
	git commit -am "Bump version to $(shell poetry version | tail -c +20) from GitHub Actions"
	git push origin main
	git tag -a v$(shell poetry version | tail -c +20) -m "v$(shell poetry version | tail -c +20)"
	git push --follow-tags

docserve:
	poetry run mkdocs serve

worker:
	poetry run celery -A example worker --loglevel=INFO

shell:
	poetry run celery shell
