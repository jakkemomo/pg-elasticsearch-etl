FROM python:3.8.3-alpine

WORKDIR /usr/src/sqlite_to_postgres

ENV PYTHONPATH="${PYTHONPATH}:/usr/src/sqlite_to_postgres"
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev

RUN pip install --upgrade pip
COPY . .
RUN pip install -r /usr/src/sqlite_to_postgres/requirements.txt

ENTRYPOINT ["/usr/src/sqlite_to_postgres/wait-for-it.sh"]
