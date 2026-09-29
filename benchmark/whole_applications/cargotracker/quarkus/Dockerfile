FROM maven:3.9.12-ibm-semeru-21-noble

RUN apt-get update && apt-get install -y --no-install-recommends curl python3 \
    && rm -rf /var/lib/apt/lists/*

ENV ARTEMIS_VERSION=2.31.2
ENV ARTEMIS_HOME=/opt/artemis
RUN curl -L -o /tmp/artemis.tar.gz "https://archive.apache.org/dist/activemq/activemq-artemis/${ARTEMIS_VERSION}/apache-artemis-${ARTEMIS_VERSION}-bin.tar.gz" \
    && mkdir -p ${ARTEMIS_HOME} \
    && tar xzf /tmp/artemis.tar.gz -C ${ARTEMIS_HOME} --strip-components=1 \
    && rm /tmp/artemis.tar.gz \
    && ${ARTEMIS_HOME}/bin/artemis create /var/lib/artemis-broker \
       --user quarkus --password quarkus --allow-anonymous --no-web --silent

WORKDIR /app
COPY . .
RUN mvn clean install -DskipTests

CMD /var/lib/artemis-broker/bin/artemis-service start && mvn quarkus:run
