.PHONY: lint build-deps upgrade-deps clean clean-docker clean-py

help:
	@echo "lint - apply isort and black formatting"
	@echo "build-deps - add/remove dependencies"
	@echo "upgrade-deps - upgrade all rependencies"
	@echo "clean - shut down containers and clean python cache and test files"

lint:
	docker-compose run --rm --no-deps --entrypoint "bash -c" web "isort -y && black --exclude venv/ --line-length 119 --target-version py37 ."

build-deps:
	docker-compose run --rm --no-deps --entrypoint "bash -c" web "pip-compile -o requirements-dev.txt requirements-dev.in requirements.in && pip-compile -o requirements.txt requirements.in"

upgrade-deps:
	docker-compose run --rm --no-deps --entrypoint "bash -c" web "pip-compile -r -U -o requirements-dev.txt requirements-dev.in requirements.in && pip-compile -r -U -o requirements.txt requirements.in"

clean: clean-docker clean-py

clean-docker:
	docker-compose down -t 60
	docker system prune -f

clean-py:
	find `pwd` -name '*.pyc' -delete
	find `pwd` -name '*.pyo' -delete
	find `pwd` -name '.coverage' -delete
	find `pwd` -name '.pytest_cache' -delete
	find `pwd` -name '__pycache__' -delete
	find `pwd` -name 'htmlcov' -delete
