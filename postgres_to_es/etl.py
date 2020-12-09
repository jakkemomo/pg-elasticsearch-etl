import json
import psycopg2
import logging
import requests

from dotenv import load_dotenv
from os import environ as env
from psycopg2.extras import RealDictCursor
from functools import wraps
from typing import List, Optional, Dict
from pydantic import BaseModel
from redis import Redis
from datetime import datetime
from time import sleep
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)


def backoff(start_sleep_time=0.1, factor=2, border_sleep_time=10):
    """
    Функция для повторного выполнения функции через некоторое время, если возникла ошибка. Использует наивный
     экспоненциальный рост времени повтора (factor) до граничного времени ожидания (border_sleep_time)

    Формула:
        t = start_sleep_time * 2^(n) if t < border_sleep_time
        t = border_sleep_time if t >= border_sleep_time
    :param start_sleep_time: начальное время повтора
    :param factor: во сколько раз нужно увеличить время ожидания
    :param border_sleep_time: граничное время ожидания
    :return: результат выполнения функции
    """

    def func_wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            time = start_sleep_time
            while time < border_sleep_time:
                time *= factor
                try:
                    return func(*args, **kwargs)
                except StopIteration:
                    return
                except Exception as e:
                    _logger.info(e)
                    print(f'Error while exucting fucntion {func}: {e}. Sleeping for {time}')
                    sleep(time)
                    func_wrapper(func)

        return inner

    return func_wrapper


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


@backoff()
def start_etl_pipeline() -> None:
    """
    Последовательная загрузка фильмов, жанров и персон из постгреса в ES.
    Раз в 60 секунд запускает etl процесс с нуля.
    """
    while True:
        data = storage.retrieve_state()
        process_movies(data)
        _logger.info("Movie update completed")
        process_genres(data)
        _logger.info("Genre update completed")
        process_persons(data)
        _logger.info("Person update completed")
        _logger.info("Pipeline completed")
        sleep(5)


@backoff()
def process_movies(data) -> None:
    """Процесс загрузкии фильмов."""
    load_movie_data = load_data()
    transform_data = transform_movie_data(load_movie_data)
    get_movie_data = postgres_loader.load_movie_data(transform_data)
    get_movie_ids = get_ids_for_update(get_movie_data)
    pre_extractor = get_pre_extract_data(get_movie_ids)
    pre_extractor.send('movie')
    pre_extractor.send(data)


@backoff()
def process_genres(data) -> None:
    """Процесс загрузкии жанров."""
    load_movie_data = load_data()
    transform_data = transform_movie_data(load_movie_data)
    get_movie_data = postgres_loader.load_movie_data(transform_data)
    get_movie_ids = postgres_loader.load_movie_ids_from_genres(get_movie_data)
    get_genre_ids = get_ids_for_update(get_movie_ids)
    pre_extractor = get_pre_extract_data(get_genre_ids)
    pre_extractor.send('genre')
    pre_extractor.send(data)


@backoff()
def process_persons(data) -> None:
    """Процесс загрузкии персон."""
    load_movie_data = load_data()
    transform_data = transform_movie_data(load_movie_data)
    get_movie_data = postgres_loader.load_movie_data(transform_data)
    get_movie_ids = postgres_loader.load_movie_ids_from_persons(get_movie_data)
    get_person_ids = get_ids_for_update(get_movie_ids)
    pre_extractor = get_pre_extract_data(get_person_ids)
    pre_extractor.send('person')
    pre_extractor.send(data)


@backoff()
@coroutine
def get_pre_extract_data(target):
    """Выгрузка данных из хранилища для выбранного направления (фильм, персона, жанр)."""
    while True:
        object_table_name = (yield)
        storage_data = (yield)
        object_data = storage_data.get(object_table_name, {})
        object_data_values = object_data.values()
        last_modified = max(object_data_values) if object_data_values else datetime(day=1, month=1, year=1800)
        target.send(object_table_name)
        target.send(last_modified)
        target.send(storage_data)


@backoff()
@coroutine
def get_ids_for_update(target):
    """
    Выгрузка айдишников из БД для выбранного направления (фильм, персона, жанр).
    table_name: назывние таблицы
    last_checkpoint: самый последний modified для выбранного направления.
    storage_data: словарь данного направления из локального хранилища.
    :return: айдишники данного направления для обновления, last_checkpoint.
    """
    while True:
        table_name = (yield)
        last_checkpoint = (yield)
        storage_data = (yield)
        query = """
                SELECT id, modified
                FROM content.%s
                WHERE modified > '%s'
                ORDER BY modified
                LIMIT 100;
            """ % (table_name, last_checkpoint)
        postgres_loader.cr.execute(query)
        data = postgres_loader.cr.fetchall()
        ids_for_update = []
        for data_object in data:
            object_id = data_object.get('id')
            modified = data_object.get('modified').strftime("%Y-%m-%d %H:%M:%S.%f")
            object_storage = storage_data.get(table_name, {})
            storage_modified = object_storage.get(object_id)
            if not storage_modified or datetime.strptime(storage_modified, "%Y-%m-%d %H:%M:%S.%f") < datetime.strptime(
                    modified, "%Y-%m-%d %H:%M:%S.%f"):
                ids_for_update.append(object_id)
                object_storage.update({object_id: modified})
            storage_data.update({table_name: object_storage})
        if not ids_for_update:
            return StopIteration
        target.send(tuple(ids_for_update))
        target.send(last_checkpoint)
        storage.save_state(storage_data)


@backoff()
@coroutine
def transform_movie_data(target):
    """Трансформация данных выбранного направления (фильм, персона, жанр) в объект Movie."""
    while True:
        data = (yield)
        movies = {}
        for line in data:
            movie_id = line['m_id']
            movie_data = dict(
                id=movie_id,
                title=line['title'],
                description=line['description'],
                imdb_rating=line['rating'],
                type=line['type'],
                created=line['created'].strftime("%Y-%m-%d %H:%M:%S.%f"),
                modified=line['modified'].strftime("%Y-%m-%d %H:%M:%S.%f")
            )
            movie = movies.get(movie_id)
            if not movie:
                # создаем новый объект фильма
                movie = Movie(**movie_data)
            person_id = line.get('p_id')
            person_name = line.get('p_name')
            person_data = [{person_id: person_name}]
            if line['role'] == 'director':
                set_person(movie.directors, person_data, person_id)
            elif line['role'] == 'actor':
                set_person(movie.actors, person_data, person_id)
            elif line['role'] == 'writer':
                set_person(movie.writers, person_data, person_id)
            genre_id = line.get('g_id')
            if not any(genre_id in p for p in movie.genres):
                movie.genres += [{genre_id: line.get('g_name')}]
            movies.update({movie_id: movie})
        movies = [movie.dict(by_alias=True) for movie in movies.values()]
        target.send(movies)


@backoff()
def set_person(field, person_data, person_id) -> None:
    """Проверяет наличие персоны в объекте фильма."""
    if not any(person_id in p for p in field):
        field += person_data


@backoff()
@coroutine
def load_data():
    """
    Загрузка в ES. Возвращает 409, если документ с таким айди уже существует.
    Принимает movie_data: Список словарей с фильмами, персонами и жанрами.
    """
    while True:
        movie_data = (yield)
        es_loader.load_to_es(movie_data, 'movies')


class ESLoader:
    def __init__(self, url: str):
        self.url = url

    @staticmethod
    def _get_es_bulk_query(rows: List[dict], index_name: str) -> List[str]:
        """
        Подготавливает bulk-запрос в Elasticsearch
        """
        prepared_query = []
        for row in rows:
            prepared_query.extend([
                json.dumps({'index': {'_index': index_name, '_id': row['id']}}),
                json.dumps(row)
            ])
        return prepared_query

    def load_to_es(self, records: List[dict], index_name: str):
        """
        Отправка запроса в ES и разбор ошибок сохранения данных
        """
        prepared_query = self._get_es_bulk_query(records, index_name)
        str_query = '\n'.join(prepared_query) + '\n'

        response = requests.post(
            urljoin(self.url, '_bulk'),
            data=str_query,
            headers={'Content-Type': 'application/x-ndjson'}
        )

        json_response = json.loads(response.content.decode())
        for item in json_response['items']:
            error_message = item['index'].get('error')
            if error_message:
                _logger.error(error_message)


class Movie(BaseModel):
    """Схема для загрузки фильмов."""

    id: str
    title: str
    description: Optional[str] = ''
    imdb_rating: Optional[float] = None
    type: Optional[str] = ''
    created: str
    modified: str
    actors: Optional[List[Dict[str, str]]] = []
    writers: Optional[List[Dict[str, str]]] = []
    directors: Optional[List[Dict[str, str]]] = []
    genres: Optional[List[Dict[str, str]]] = []


class PostgresLoader:
    @backoff()
    def __init__(self):
        """
        1) Инициализация PostgreSQL.
        2) Обеспечения доступа к курсору из любого метода класса.
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

    @backoff()
    @coroutine
    def load_movie_ids_from_genres(self, target):
        """Выгрузка айдишников фильмов, связанных с жанрами,
         айди которых в ids и датой обновления из last_checkpoint."""
        while True:
            ids = (yield)
            last_checkpoint = (yield)
            movie_ids_query = f"""
                            SELECT m.id, m.modified
                            FROM content.movie m
                            LEFT JOIN content.movie_genre_rel mgr ON mgr.movie_id = m.id
                            WHERE m.modified > '{last_checkpoint}' AND mgr.genre_id IN {ids}
                            ORDER BY m.modified
                            LIMIT 100;
                            """
            self.cr.execute(movie_ids_query)
            movie_data = self.cr.fetchall()
            movie_ids = (m['id'] for m in movie_data)
            target.send(movie_ids)

    @backoff()
    @coroutine
    def load_movie_ids_from_persons(self, target):
        """Выгрузка айдишников фильмов, связанных с персонами,
         айди которых в ids и датой обновления из last_checkpoint."""
        while True:
            ids = (yield)
            last_checkpoint = (yield)
            movie_ids_query = f"""
                            SELECT m.id, m.modified
                            FROM content.movie m
                            LEFT JOIN content.movie_person_rel pm ON pm.movie_id = m.id
                            WHERE m.modified > '{last_checkpoint}' AND pm.person_id IN {ids}
                            ORDER BY m.modified
                            LIMIT 100;
                            """
            self.cr.execute(movie_ids_query)
            movie_data = self.cr.fetchall()
            movie_ids = (m['id'] for m in movie_data)
            target.send(movie_ids)

    @backoff()
    @coroutine
    def load_movie_data(self, target):
        """Выгрузка информации по фильмам, айди которых приходит в ids."""
        while True:
            ids = (yield)
            last_checkpoint = (yield)
            movies_query = f"""
                            SELECT
                                m.id as m_id,
                                m.title,
                                m.description,
                                m.rating,
                                m.type,
                                m.created,
                                m.modified,
                                movie_person.role as role,
                                p.id as p_id,
                                p.name as p_name,
                                g.id as g_id,
                                g.name as g_name
                            FROM content.movie m
                            LEFT JOIN content.movie_person_rel movie_person ON movie_person.movie_id = m.id
                            LEFT JOIN content.person p ON p.id = movie_person.person_id
                            LEFT JOIN content.movie_genre_rel gm ON gm.movie_id = m.id
                            LEFT JOIN content.genre g ON g.id = gm.genre_id
                            where m.id in {ids};
                            """
            self.cr.execute(movies_query)
            movie_data = self.cr.fetchall()
            target.send(movie_data)


class RedisStorage:
    def __init__(self, redis_adapter: Redis):
        self.redis_adapter = redis_adapter

    @backoff()
    def save_state(self, state: dict) -> None:
        """
         Сохранение состояния в Редис.
         Архитектура данных следующая:
        {'data':
         {'movie': {'id': 'modified', ...}},
         {'genre': {'id': 'modified', ...},
         {'person': {'id': 'modified', ...}}
        }
        """
        self.redis_adapter.set('data', json.dumps(state))

    @backoff()
    def retrieve_state(self) -> dict:
        """Получение сохренных данных из Редиса в виде словаря."""
        raw_data = self.redis_adapter.get('data')
        if raw_data is None:
            return {}
        return json.loads(raw_data)


if __name__ == "__main__":
    storage = RedisStorage(Redis(decode_responses=True))
    postgres_loader = PostgresLoader()
    es_loader = ESLoader(url="http://127.0.0.1:9200/")
    start_etl_pipeline()
