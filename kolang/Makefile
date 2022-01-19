
VER := $(shell sed -nE  '/^__version__/ { s/^.*=\s*(["'"'"'])(.*)\1.*$$/\2/; p }' kolang/__init__.py)

dist/kolang-$(VER): build/kolang.pyz
	mkdir -p dist
	cp build/kolang.pyz dist/kolang-$(VER)

build/kolang.pyz: Makefile kolang/__init__.py
	rm -rf build/kolang
	mkdir -p build/kolang
	python3 -m pip install -r requirements.txt --target build/kolang
	cp -r kolang build/kolang/kolang
	cp -r kolang/__main__.py build/kolang
	find -name __pycache__ -print0 | xargs -0 rm -r
	rm -r build/kolang/*.dist-info
	( cd build && python3 -m zipapp -p '/usr/bin/env python3' kolang )

