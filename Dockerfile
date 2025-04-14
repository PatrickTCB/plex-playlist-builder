FROM python:3

RUN mkdir app
ADD ./conf.toml app/
ADD ./playlists.toml app/
ADD ./main.py app/

RUN python3 -m pip install xmltodict
RUN python3 -m pip install requests
RUN python3 -m pip install tzdata

ENV BUILDID=""

ENV RUNHOUR=18
ENV TIMEZONE="Europe/Berlin"

WORKDIR /app/

CMD [ "python3", "-u", "main.py" ]