DOCKER ?= docker
BUSINESS_DOMAIN_TARGET := spring
CONTAINER_KEY := $(shell printf '%s' '$(CURDIR)' | cksum | cut -d' ' -f1)
IMAGE_ID_FILE := /tmp/scarfbench-converter-$(CONTAINER_KEY).image-id
CONTAINER_NAME ?= scarfbench-converter-$(CONTAINER_KEY)

.PHONY: build up down test

build:
	rm -f $(IMAGE_ID_FILE)
	$(DOCKER) build --iidfile $(IMAGE_ID_FILE) .
	@echo BUILD SUCCESS

up: build
	-$(DOCKER) rm -f $(CONTAINER_NAME) >/dev/null 2>&1
	$(DOCKER) run -d --name $(CONTAINER_NAME) $$(cat $(IMAGE_ID_FILE))

down:
	-$(DOCKER) rm -f $(CONTAINER_NAME) >/dev/null 2>&1
	@if test -s $(IMAGE_ID_FILE); then $(DOCKER) image rm $$(cat $(IMAGE_ID_FILE)) >/dev/null 2>&1 || true; fi
	-rm -f $(IMAGE_ID_FILE)

test: up
	@status=1; trap '$(MAKE) down DOCKER=$(DOCKER) >/dev/null 2>&1' EXIT; \
	if $(DOCKER) exec -e BUSINESS_DOMAIN_TARGET=$(BUSINESS_DOMAIN_TARGET) $(CONTAINER_NAME) bash /app/test.sh; then \
	  echo '===== 1 passed ====='; status=0; \
	fi; exit $$status
