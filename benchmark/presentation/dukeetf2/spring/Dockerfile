FROM maven:3.9.12-ibm-semeru-21-noble

USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl python3 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy all the assets
COPY . .

COPY test.sh .
RUN chmod +x test.sh

# Build application at image build time
RUN mvn clean install -DskipTests

CMD ["mvn", "spring-boot:run"]
