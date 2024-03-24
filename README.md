## Описание запуска

### 1. Создать .env файлы для load_env() в директориях

### movies_admin/config/settings

    database=postgres
    db_host=db
    db_port=5432
    db_name=movies
    db_user=jaqombo
    db_password=12345
    db_scheme=content
    secret_key=some-key
### sqlite_to_postgres

    db_host=db
    db_port=5432
    db_name=movies
    db_user=jaqombo
    db_password=12345
    db_scheme=content
    db_path=db.sqlite

### postgres_to_es

    db_host=db
    db_port=5432
    db_name=movies
    db_user=jaqombo
    db_password=12345
    db_scheme=content

### 2. sudo docker-compose up

#

### Опционально

Проверка Django

    curl -i 0.0.0.0:1337/admin

Создать пользователя в Django

    sudo docker exec -it django_web python /usr/src/web/manage.py createsuperuser

Проверка ES

    curl -i 0.0.0.0:8881

Проврка Kibana

    curl -i 0.0.0.0:8882

Проверить загруженные фильмы в ES можно по ссылке

    0.0.0.0:8881/movies/_search
