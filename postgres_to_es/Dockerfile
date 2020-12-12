FROM python:3.8.3-alpine

WORKDIR /usr/src/postgres_to_es

ENV PYTHONPATH=/usr/src/postgres_to_es/src:${PYTHONPATH}
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apk update \
    && apk add postgresql-dev gcc python3-dev musl-dev

RUN pip install --upgrade pip
COPY . .
RUN pip install -r postgres_to_es/production.txt

CMD ["python", "main.py"]
