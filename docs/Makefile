.PHONY: all
all:
	rm -rf build
	sphinx-apidoc -F -o build ../splunksolutionlib/
	cp sphinx_conf.py build/conf.py
	make -C build html

.PHONY: clean
clean:
	rm -rfv build
