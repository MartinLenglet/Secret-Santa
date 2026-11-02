PYTHON ?= python

.PHONY: help install dev test build start lint
help:
	@$(PYTHON) manage.py help
install:
	$(PYTHON) manage.py install
dev:
	$(PYTHON) manage.py dev
test:
	$(PYTHON) manage.py test
build:
	$(PYTHON) manage.py build
start:
	$(PYTHON) manage.py start
lint:
	$(PYTHON) manage.py lint
