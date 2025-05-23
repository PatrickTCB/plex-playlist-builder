FROM python:3

RUN mkdir app
ADD ./conf.toml app/
ADD ./playlists.toml app/
ADD ./main.py app/

RUN python3 -m pip install xmltodict
RUN python3 -m pip install requests
RUN python3 -m pip install tzdata

ARG BUILDID
RUN echo "Build ID - $BUILDID" > /app/buildid.txt

ENV RUNHOUR=18
ENV TIMEZONE="Europe/Berlin"

WORKDIR /app/

CMD [ "python3", "-u", "main.py" ]