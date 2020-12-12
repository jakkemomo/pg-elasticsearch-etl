#!/bin/sh
python /usr/src/web/manage.py flush --no-input
python /usr/src/web/manage.py migrate --fake movies 0001
python /usr/src/web/manage.py migrate