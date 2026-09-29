DOCKER ?= docker
CONTAINER_KEY := $(shell printf '%s' '$(CURDIR)' | cksum | cut -d' ' -f1)
IMAGE_ID_FILE := /tmp/scarfbench-cargotracker-$(CONTAINER_KEY).image-id
CONTAINER_NAME ?= scarfbench-cargotracker-$(CONTAINER_KEY)

.PHONY: build up down test

build:
	rm -f $(IMAGE_ID_FILE)
	$(DOCKER) build --iidfile $(IMAGE_ID_FILE) .
	@echo BUILD SUCCESS

up: build
	-$(DOCKER) rm -f $(CONTAINER_NAME) >/dev/null 2>&1
	$(DOCKER) run -d --name $(CONTAINER_NAME) -e QUARKUS_HTTP_PORT=8080 $$(cat $(IMAGE_ID_FILE))

down:
	-$(DOCKER) rm -f $(CONTAINER_NAME) >/dev/null 2>&1
	-rm -f $(IMAGE_ID_FILE)

test: up
	@status=1; trap '$(MAKE) down DOCKER=$(DOCKER) >/dev/null 2>&1' EXIT; \
	if $(DOCKER) exec $(CONTAINER_NAME) bash test.sh; then \
	  echo '===== 1 passed ====='; status=0; \
	fi; exit $$status
