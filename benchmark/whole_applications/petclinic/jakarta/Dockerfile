FROM maven:3.9.12-ibm-semeru-21-noble

USER root
# Runtime tools for the database and shared behavior test.
RUN apt-get update && apt-get install -y --no-install-recommends python3 postgresql postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Initialize PostgreSQL database at build time
RUN pg_lsclusters | tail -1 | awk '{print $1, $2}' > /tmp/pgver.txt \
    && PG_VERSION=$(cut -d' ' -f1 /tmp/pgver.txt) \
    && PG_CLUSTER=$(cut -d' ' -f2 /tmp/pgver.txt) \
    && pg_ctlcluster ${PG_VERSION} ${PG_CLUSTER} start \
    && su - postgres -c "psql -c \"CREATE USER petclinic_jakartaee WITH PASSWORD 'petclinic_jakartaeepwd';\"" \
    && su - postgres -c "psql -c \"CREATE DATABASE petclinic_jakartaee_liberty OWNER petclinic_jakartaee;\"" \
    && su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE petclinic_jakartaee_liberty TO petclinic_jakartaee;\"" \
    && pg_ctlcluster ${PG_VERSION} ${PG_CLUSTER} stop

# Set working directory
WORKDIR /app

# Copy all the assets
COPY . .

RUN if [ -f mvnw ]; then chmod +x mvnw; fi && if [ -f smoke.py ]; then chmod +x smoke.py; fi && if [ -f test.sh ]; then chmod +x test.sh; fi

RUN mvn -Pliberty -DskipTests package

CMD pg_lsclusters | tail -1 | awk '{print $1, $2}' > /tmp/pgver.txt \
    && PG_VERSION=$(cut -d' ' -f1 /tmp/pgver.txt) \
    && PG_CLUSTER=$(cut -d' ' -f2 /tmp/pgver.txt) \
    && pg_ctlcluster ${PG_VERSION} ${PG_CLUSTER} start \
    && exec mvn -Pliberty -DskipTests liberty:run
