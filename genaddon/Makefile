
VER := $(shell sed -nE  '/^__version__/ { s/^.*=\s*(["'"'"'])(.*)\1.*$$/\2/; p }' genaddon/__init__.py)

dist/genaddon-$(VER).pyz: build/genaddon.pyz
	mkdir -p dist
	cp build/genaddon.pyz dist/genaddon-$(VER).pyz

build/genaddon.pyz: Makefile genaddon/__init__.py
	rm -rf build/genaddon
	mkdir -p build/genaddon
	python3 -m pip install -r requirements.txt --target build/genaddon
	cp -r genaddon build/genaddon/genaddon
	sed 's/^from [.]/from genaddon./; s/^import [.]/import genaddon./' genaddon/__main__.py > build/genaddon/__main__.py
	find -name __pycache__ -print0 | xargs -0 rm -rf
	rm -rf build/genaddon/*.dist-info
	( cd build && python3 -m zipapp -p '/usr/bin/env python3' genaddon )

