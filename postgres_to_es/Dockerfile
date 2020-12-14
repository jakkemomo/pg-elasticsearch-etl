FROM python:3.8.3-alpine

WORKDIR /usr/src/postgres_to_es

ENV PYTHONPATH="/usr/src:${PYTHONPATH}"
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev && apk --no-cache add curl

RUN pip install --upgrade pip
COPY . .
RUN pip install -r /usr/src/postgres_to_es/requirements.txt

ENTRYPOINT ["sh", "entrypoint.sh"]