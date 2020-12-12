# Описание структуры и порядок выполнения проекта:
1. `schema_design` - раздел c материалами для новой архитектуры базы данных.
2. `sqlite_to_postgres` - раздел с материалами по миграции данных.
3. `movies_admin` - раздел с материалами для панели администратора.

# Docker Start of Django, Postgres, ES, Kibana and Nginx
1. sudo docker-compose up -d
2. sudo docker exec django_web /usr/src/web/setup_db.sh
3. sudo docker exec django_web /usr/src/web/start_django.sh
4. sudo docker exec django_web python /usr/src/postgres_to_es/load_es_schema.py
5. sudo docker exec django_web python /usr/src/postgres_to_es/etl.py
6. sudo docker exec django_web python manage.py collectstatic --no-input --clear
7. Опционально sudo docker exec -it django_web python /usr/src/web/manage.py createsuperuser
8. Опционально Проверка Django curl -i 0.0.0.0:1337/admin
9. Опционально Проверка ES curl -i 0.0.0.0:8881
10. Опционально Проверка Kibana curl -i 0.0.0.0:8882
11. Опционально sudo docker exec redis_db redis-cli flushdb