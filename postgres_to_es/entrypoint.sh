#!/bin/bash

>&2 echo "Loading from postgres to es - sleeping"

until curl elasticsearch:9200; do
  >&2 echo "Loading from postgres to es - sleeping"
  sleep 5
done

>&2 echo "Loading schema to es"
python src/load_es_schema.py
>&2 echo "Schema loaded to es"

exec "$@"
