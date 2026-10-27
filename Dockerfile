FROM python:3-alpine

RUN apk add --no-cache tzdata
ENV TZ=Etc/UTC

WORKDIR /opt/navidrome-mix/

ADD ./requirements.txt .
RUN pip install -r requirements.txt

COPY ./docker/start.sh /start.sh
COPY ./src .

# Can be defined from compose as well
ENV MIX_UPDATE_SCHEDULE="0 2 * * *"

CMD ["/start.sh"]