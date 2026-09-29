FROM maven:3.9.12-ibm-semeru-21-noble

USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy all the assets
COPY . .

RUN if [ -f mvnw ]; then chmod +x mvnw; fi && if [ -f smoke.py ]; then chmod +x smoke.py; fi && if [ -f test.sh ]; then chmod +x test.sh; fi

CMD [ "mvn", "clean", "-DskipTests", "spring-boot:run" ]
