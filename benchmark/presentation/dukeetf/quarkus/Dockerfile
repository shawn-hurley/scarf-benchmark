FROM maven:3.9.12-ibm-semeru-21-noble

USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy all the assets
COPY . .

# Build the application at image build time
RUN mvn clean install -DskipTests

COPY test.sh .
RUN chmod +x test.sh

RUN mvn clean install -DskipTests

CMD ["mvn", "quarkus:run"]
