# based on think/plantuml
# https://hub.docker.com/r/think/plantuml
# https://github.com/lindt/docker_plantuml

FROM gtavali/alpine-oraclejdk8

MAINTAINER think@hotmail.de

ENV PLANTUML_VERSION=1.2019.11

RUN mkdir /metadata
RUN env TZ=UTC date +%Y-%m-%dT%H:%M:%SZ > /metadata/build-timestamp
COPY Dockerfile /metadata

RUN \
  apk add --no-cache graphviz wget ca-certificates && \
  mkdir -p /opt/plantuml && \
  wget "http://downloads.sourceforge.net/project/plantuml/${PLANTUML_VERSION}/plantuml.${PLANTUML_VERSION}.jar" -O /opt/plantuml/plantuml.jar && \
  apk del wget ca-certificates

ENV LANG en_US.UTF-8

ENTRYPOINT ["java", "-Djava.awt.headless=true", "-Dfile.encoding=UTF-8", "-jar", "/opt/plantuml/plantuml.jar"]

CMD ["-tsvg"]