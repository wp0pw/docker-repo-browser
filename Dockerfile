FROM python:3.3.6-slim

RUN pip3 install requests

RUN pip3 install Flask

ADD src /opt/src

WORKDIR /opt/src

EXPOSE 8081

CMD python3 start.py

