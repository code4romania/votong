lint:
	 black --exclude venv/ --line-length 120 --target-version py37 .

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
