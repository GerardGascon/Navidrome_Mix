FROM python:3-alpine

WORKDIR /opt/navidrome-mix/

COPY ./docker/start.sh /start.sh
COPY ./src .

RUN pip install -r requirements.txt

# Can be defined from compose as well
ENV MIX_UPDATE_SCHEDULE="0 2 * * *"

CMD ["/start.sh"]