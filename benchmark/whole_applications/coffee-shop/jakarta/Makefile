DOCKER ?= docker
CONTAINER_KEY := $(shell printf '%s' '$(CURDIR)' | cksum | cut -d' ' -f1)
IMAGE_ID_FILE := /tmp/scarfbench-coffee-shop-$(CONTAINER_KEY).image-id
CONTAINER_NAME ?= scarfbench-coffee-shop-$(CONTAINER_KEY)
NETWORK_NAME := $(CONTAINER_NAME)-net
DB_NAME := $(CONTAINER_NAME)-db
KAFKA_NAME := $(CONTAINER_NAME)-kafka

.PHONY: build up down test

build:
	rm -f $(IMAGE_ID_FILE)
	$(DOCKER) build --iidfile $(IMAGE_ID_FILE) .
	@echo BUILD SUCCESS

up: build
	-$(DOCKER) rm -f $(CONTAINER_NAME) $(DB_NAME) $(KAFKA_NAME) >/dev/null 2>&1
	-$(DOCKER) network rm $(NETWORK_NAME) >/dev/null 2>&1
	$(DOCKER) network create $(NETWORK_NAME)
	$(DOCKER) run -d --name $(DB_NAME) --network $(NETWORK_NAME) --network-alias postgres \
		-e POSTGRES_USER=cafe -e POSTGRES_PASSWORD=cafe -e POSTGRES_DB=coffeeshop \
		postgres:16
	$(DOCKER) exec $(DB_NAME) sh -c 'until pg_isready -U cafe -d coffeeshop >/dev/null 2>&1; do sleep 1; done'
	@printf '%s\n' 'CREATE TABLE IF NOT EXISTS orders (id BIGSERIAL PRIMARY KEY, customer VARCHAR(100) NOT NULL, item VARCHAR(100) NOT NULL, quantity INTEGER NOT NULL CHECK (quantity > 0), status VARCHAR(20) NOT NULL, created TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated TIMESTAMPTZ NOT NULL DEFAULT NOW());' | $(DOCKER) exec -i $(DB_NAME) psql -U cafe -d coffeeshop
	$(DOCKER) run -d --name $(KAFKA_NAME) --network $(NETWORK_NAME) --network-alias kafka \
		docker.io/redpandadata/redpanda:v23.2.14 redpanda start \
		--overprovisioned --smp 1 --memory 1G --reserve-memory 0M --node-id 0 --check=false \
		--kafka-addr 0.0.0.0:9092 --advertise-kafka-addr kafka:9092
	$(DOCKER) run -d --name $(CONTAINER_NAME) --network $(NETWORK_NAME) \
		-e DB_HOST=postgres -e DB_PORT=5432 -e DB_NAME=coffeeshop \
		-e DB_USER=cafe -e DB_PASSWORD=cafe -e KAFKA_BOOTSTRAP=kafka:9092 \
		$$(cat $(IMAGE_ID_FILE))

down:
	-$(DOCKER) rm -f $(CONTAINER_NAME) $(DB_NAME) $(KAFKA_NAME) >/dev/null 2>&1
	-$(DOCKER) network rm $(NETWORK_NAME) >/dev/null 2>&1
	-rm -f $(IMAGE_ID_FILE)

test: up
	@status=1; trap '$(MAKE) down DOCKER=$(DOCKER) >/dev/null 2>&1' EXIT; \
	if $(DOCKER) exec -e COFFEE_SHOP_TARGET=jakarta $(CONTAINER_NAME) bash /app/test.sh; then \
	  echo '===== 1 passed ====='; status=0; \
	fi; exit $$status
