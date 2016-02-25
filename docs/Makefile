.PHONY: all
all:
	rm -rf build
	sphinx-apidoc -F -o build ../splunksolutionlib/
	cp templates/conf.py build/
	make -C build html

.PHONY: clean
clean:
	rm -rfv build
