FROM maven:3.9.9-ibm-semeru-11-focal

RUN apt-get update && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY pom.xml .
COPY src ./src
COPY test.sh .
RUN mvn -B -DskipTests package

CMD ["mvn", "clean", "-DskipTests", "package", "cargo:run"]
