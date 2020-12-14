#!/bin/sh

if [ "$database" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $db_host $db_port; do
      sleep 0.1
    done

    echo "PostgreSQL started"

fi

sleep 3

python /usr/src/web/manage.py flush --no-input
python /usr/src/web/manage.py migrate --fake movies 0001
python /usr/src/web/manage.py migrate
python /usr/src/web/manage.py collectstatic --no-input --clear

exec "$@"
