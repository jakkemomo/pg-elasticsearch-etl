FROM python:3.8.3-alpine

WORKDIR /usr/src/web

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev

RUN pip install --upgrade pip
COPY . .
RUN echo $(ls)
RUN pip install -r requirements/production.txt
ENTRYPOINT ["/usr/src/web/entrypoint.sh"]
