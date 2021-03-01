#!/bin/sh

>&2 echo "Check DB availability"

while ! nc -z $db_host $db_port; do
  >&2 echo "sqlite_to_postgres is unavailable - sleeping"
  sleep 2
done

>&2 echo "sqlite_to_postgres is up - executing command"
exec "$@"
