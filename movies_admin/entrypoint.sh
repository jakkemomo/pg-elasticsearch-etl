#!/bin/sh
export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
if [ "$database" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $db_host $db_port; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

exec "$@"
