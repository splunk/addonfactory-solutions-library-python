.PHONY: all
all: init

.PHONY: init
init:
	pip install -r requirements.txt

.PHONY: test
test:
	py.test tests

.PHONY: coverage
coverage:
	py.test --verbose --cov-report term --cov=splunksolutionlib tests

.PHONY: install
install:
	python setup.py install --record install_record.txt

.PHONY: uninstall
uninstall:
	cat install_record.txt|xargs rm -rfv
	rm -rf install_record.txt

.PHONY: docs
docs:
	make -C docs

.PHONY: clean
clean:
	rm -rfv .cache
	rm -rfv .eggs
	rm -rfv .coverage*
	rm -rfv build
	rm -rfv dist
	rm -rfv splunksolutionlib.egg-info
	rm -rfv tests/__pycache__
	find . -name "*.pyc"|xargs rm -rfv
	make -C docs clean
