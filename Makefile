PYCODESTYLE_MAX_LINE_LENGTH=512
.PHONY: all checkmake clean lint shellcheck style test unittest

all: checkmake shellcheck style lint test

checkmake:
	checkmake ./Makefile

clean:

lint:
	pylint --rcfile=./.pylintrc *.py || true

shellcheck:
	shellcheck 1 || true

style:
	pycodestyle --max-line-length=${PYCODESTYLE_MAX_LINE_LENGTH} *.py || true

unittest:
#	python -m unittest tests/*.py

test: unittest
