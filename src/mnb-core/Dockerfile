FROM python:3.10-alpine

#install git for git-python
RUN apk add git

ARG MNB_RUN=/mnb/run
ARG MNB_LIB=/mnb/lib

COPY src/mnb-spec ${MNB_LIB}/mnb-spec
COPY src/mnb-core ${MNB_LIB}/mnb-core
ENV PYTHONPATH=$MNB_LIB/mnb-spec:$MNB_LIB/mnb-core:$MNB_RUN
RUN pip3 install -r ${MNB_LIB}/mnb-core/requirements.txt

WORKDIR ${MNB_RUN}
ENTRYPOINT ["/usr/local/bin/python3", "/mnb/lib/mnb-core/main.py" ]

