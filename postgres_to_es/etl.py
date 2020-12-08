from time import sleep

import psycopg2
import backoff
import requests
import logging

from dotenv import load_dotenv
from os import environ as env
from elasticsearch import Elasticsearch
from psycopg2.extras import RealDictCursor
from functools import wraps


def coroutine(func):
    @wraps(func)
    def inner(*args, **kwargs):
        fn = func(*args, **kwargs)
        next(fn)
        return fn

    return inner


load_dotenv()
db_host = env["db_host"]
db_port = env["db_port"]
db_name = env["db_name"]
db_user = env["db_user"]
db_password = env["db_password"]
db_scheme = env["db_scheme"]


def load_from_postgres() -> None:
    """
    Основной метод загрузки данных из Postgres в ES.
    """
    postgres_loader = PostgresLoader()

    # сначала проверяем фильмы
    # для этого проверяем через редис, актуальное ли состояние у нас
    # делаем запрос в базу по всем фильмам, забираем updated_at
    # если айдишника с этим фильмом нет в базе или у него, то добавляем его в список айдишников на загруку
    # так же в список айдишников на добавление попадают все фильмы, у которых updated_at ме совпадает со значением в редисе
    # собираем все данные из постгреса по фильму, его персонам и жанрам
    # трансформируем это в приемлемый для ес вид и загружаем
    # get_ids_for_update('movie', )
    # затем проверяем жанры
    # точно также смотрим в редисе наличие всех айдишников жанров и совпадение поля updated_at
    # при несоответствии, добавляем айдишник в список для загрузки
    # собираем все данные по фильмам с этими жанрами и обновляем их

    # точно также проверяем персоны и при измении персон обновляем все связанные с этой персоной фильмы
    data = postgres_loader.load_data()

    import_data(data)


def start_etl_pipeline(target):
    while True:
        # раз в 60 секунд запускать etl процесс
        # вызов метода для проверки состояния фильмов
        sleep(60)


def get_ids_for_update(table_name: str, data: dict):
    # last_checkpoint = забираем из редиса последний updated_at для выбранного направления
    last_checkpoint = 1
    query = """
            SELECT id, modified
            FROM content.%s
            WHERE updated_at > %s
            ORDER BY updated_at
            LIMIT 100;
        """ % (table_name, last_checkpoint)
    ids_for_update = []
    for id, updated_at in data.items():
        if get_state(id) != updated_at:
            ids_for_update.append(id)
    return ids_for_update


def import_data(movies):
    """Метод для загрузки данных в ES."""

    for movie in movies:
        writer_data, writers_names = [], []
        actor_data, actors_names = [], []
        movie_body = dict(id=movie['id'],
                          imdb_rating=movie['rating'],
                          genre=movie[2],
                          title=movie[3],
                          description=movie[4],
                          director=movie[5],
                          actors_names=actors_names,
                          writers_names=writers_names,
                          actors=actor_data,
                          writers=writer_data)
        create_new_movie(index="movies", id=movie['id'], body=movie_body)


def create_new_movie(index, id, body):
    """
    Создает новый документ в рамках индекса. Возвращает 409, если документ с таким айди уже существует.
    :param index: Индекс для записи в ES.
    :param body: Тело запроса с данными фильма.
    """
    try:
        es.create(index=index, id=id, body=body, doc_type=None, params=None, headers=None)
    except Exception as e:
        logging.info(e)


class PostgresLoader:
    @backoff.on_exception(backoff.expo,
                          (requests.exceptions.Timeout,
                           requests.exceptions.ConnectionError))
    def __init__(self):
        """
        1) Инициализация PostgreSQL.
        2) Обеспечения доступа к курсору из любого метода.
        """
        self.connection = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            options=f"-c search_path={db_scheme}"
        )
        self.cr = self.connection.cursor(cursor_factory=RealDictCursor)

    def load_person_data(self) -> list:
        # last_modified = get_state()
        person_query_1 = """
                        SELECT id, updated_at
                        FROM content.person
                        WHERE updated_at > %s
                        ORDER BY updated_at
                        LIMIT 100;
                    """
        # person_query_3 = """
        #             SELECT
        #                 m.id as m_id,
        #                 m.title,
        #                 m.description,
        #                 m.rating,
        #                 m.type,
        #                 m.created,
        #                 m.modified,
        #                 movie_person.role,
        #                 p.id,
        #                 p.name,
        #                 g.name
        #             FROM content.movie m
        #             LEFT JOIN content.movie_person_rel movie_person ON movie_person.movie_id = m.id
        #             LEFT JOIN content.person p ON p.id = movie_person.person_id
        #             LEFT JOIN content.movie_genre_rel gm ON gm.movie_id = m.id
        #             LEFT JOIN content.genre g ON g.id = gm.genre_id;
        #             """
        self.cr.execute(person_query_1)
        data = self.cr.fetchall()
        return data

    def load_movie_data(self):
        return

    def load_genre_data(self):
        return


if __name__ == "__main__":
    es = Elasticsearch()
    load_from_postgres()
