FROM python:3

RUN mkdir app
ADD ./app app/

RUN python3 -m pip install xmltodict
RUN python3 -m pip install requests
RUN python3 -m pip install tzdata

ENV RUNHOUR=18
ENV TIMEZONE="Europe/Berlin"

WORKDIR /app/

CMD [ "python3", "-u", "main.py" ]