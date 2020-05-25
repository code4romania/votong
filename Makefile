lint:
	black --exclude venv/ --line-length 119 --target-version py37 .

build-deps:
	pip-compile -r -o requirements-dev.txt requirements-dev.in requirements.in
	pip-compile -o requirements.txt requirements.in

upgrade-deps:
	pip-compile -r -U -o requirements-dev.txt requirements-dev.in requirements.in
	pip-compile -U -o requirements.txt requirements.in

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
