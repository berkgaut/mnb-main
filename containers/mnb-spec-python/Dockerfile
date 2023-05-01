FROM python:3.10-alpine

ARG MNB_RUN=/mnb/run
ARG MNB_LIB=/mnb/lib

WORKDIR ${MNB_RUN}
COPY src/mnb-spec ${MNB_LIB}/mnb-spec
ENV PYTHONPATH=$MNB_LIB/mnb-spec:$MNB_RUN

