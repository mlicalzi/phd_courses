.PHONY: help validate build serve clean

help:
	@echo "make validate   check data/*.json against the schema"
	@echo "make build      generate ./site"
	@echo "make serve      build, then serve on http://localhost:8000"

validate:
	python scripts/validate.py

build: validate
	python scripts/build_site.py

serve: build
	python -m http.server 8000 --directory site

clean:
	rm -rf site
