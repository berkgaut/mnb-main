# docker build -t bberkgaut/mnb:latest .

FROM python:3.9

RUN mkdir /mnb
RUN mkdir /mnb/lib

ADD requirements.txt /mnb/lib/mnb/requirements.txt
RUN pip3 install -r /mnb/lib/mnb/requirements.txt

ENV PYTHONPATH=/mnb/lib

WORKDIR /mnb/run
ENTRYPOINT [ "/usr/local/bin/python3", "/mnb/lib/mnb/climain.py" ]

RUN mkdir /mnb/lib/scripts
ADD scripts/* /mnb/lib/scripts/

ADD mnb/*.py /mnb/lib/mnb/
#TODO: install git for git-python
