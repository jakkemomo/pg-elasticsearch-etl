import logging
import psycopg2
import backoff
import os.path
import sys

from psycopg2.extras import RealDictCursor
from functools import wraps
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime
from time import sleep

PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from postgres_to_es.storage import RedisStorage, Redis
from postgres_to_es.es_loader import ESLoader
from postgres_to_es.settings import db_user, db_port, db_host, db_name, db_password, db_scheme, sleep_time

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)


def coroutine(func):
    @wraps(func)
    def inner(*args, **kwargs):
        fn = func(*args, **kwargs)
        next(fn)
        return fn

    return inner


class ETL:
    def __init__(self):
        self.redis_storage = storage.retrieve_state()

    @backoff.on_exception(backoff.expo, Exception)
    def start_etl_pipeline(self) -> None:
        """
        Последовательная загрузка фильмов, жанров и персон из постгреса в ES.
        Раз в sleep_time секунд запускает etl процесс с нуля.
        """
        while True:
            self.process_movies()
            _logger.info("Movie update completed")
            self.process_genres()
            _logger.info("Genre update completed")
            self.process_persons()
            _logger.info("Person update completed")
            sleep(sleep_time)

    @backoff.on_exception(backoff.expo, Exception)
    def process_movies(self) -> None:
        """Процесс загрузкии фильмов."""
        process_movies = self.process_movie_data()
        get_movie_ids = self.get_ids_for_update(process_movies)
        self.get_pre_extract_data(get_movie_ids, 'movie')

    @backoff.on_exception(backoff.expo, Exception)
    def process_genres(self) -> None:
        """Процесс загрузкии жанров."""
        process_movies = self.process_movie_data()
        get_movie_ids = postgres_loader.load_movie_ids_from_related_table(process_movies, 'movie_genre_rel', 'genre_id')
        get_related_ids = self.get_ids_for_update(get_movie_ids)
        self.get_pre_extract_data(get_related_ids, 'genre')

    @backoff.on_exception(backoff.expo, Exception)
    def process_persons(self) -> None:
        """Процесс загрузкии персон."""
        get_movie_data = self.process_movie_data()
        get_movie_ids = postgres_loader.load_movie_ids_from_related_table(
            get_movie_data, 'movie_person_rel', 'person_id')
        get_related_ids = self.get_ids_for_update(get_movie_ids)
        self.get_pre_extract_data(get_related_ids, 'person')

    def process_movie_data(self):
        """ Из необходимых для обновлений id фильмов собрать данные по этим фильмам."""
        load_movie_data = self.load_data()
        transform_data = self.transform_movie_data(load_movie_data)
        get_movie_data = postgres_loader.load_movie_data(transform_data)
        return get_movie_data

    @backoff.on_exception(backoff.expo, Exception)
    def get_pre_extract_data(self, target, object_table_name: str):
        """Выгрузка данных из хранилища для выбранного направления (фильм, персона, жанр)."""
        object_data: dict = self.redis_storage.get(object_table_name, {})
        object_data_values = object_data.values()
        # забираем последнюю дату обновления объекта либо значение по умолчанию
        last_modified = max(object_data_values) if object_data_values else datetime(day=1, month=1, year=1800)
        target.send(object_table_name)
        target.send(last_modified)

    @backoff.on_exception(backoff.expo, Exception)
    @coroutine
    def get_ids_for_update(self, target):
        """
        Выгрузка айдишников из БД для выбранного направления (фильм, персона, жанр).
        table_name: назывние таблицы
        last_checkpoint: самый последний modified для выбранного направления.
        storage_data: словарь данного направления из локального хранилища.
        :return: айдишники данного направления для обновления, last_checkpoint.
        """
        while True:
            table_name: str = (yield)
            last_checkpoint: datetime = (yield)
            query = """
                    SELECT id, modified
                    FROM content.%s
                    WHERE modified > '%s'
                    ORDER BY modified
                    LIMIT 100;
                """ % (table_name, last_checkpoint)
            postgres_loader.cr.execute(query)
            object_ids = postgres_loader.cr.fetchall()
            ids_for_update = []
            for obj in object_ids:
                object_id = obj.get('id')
                modified = obj.get('modified').strftime("%Y-%m-%d %H:%M:%S.%f")
                table_storage = self.redis_storage.get(table_name, {})
                existing_modified = table_storage.get(object_id)
                # Добавляем айди в список для обновления только в том случае, если у нас нет modified в хранилище, либо
                # modified в хранилище устарел
                if not existing_modified or self.get_str_date(existing_modified) < self.get_str_date(modified):
                    ids_for_update.append(object_id)
                    table_storage.update({object_id: modified})
                self.redis_storage.update({table_name: table_storage})
            target.send(tuple(ids_for_update))
            target.send(last_checkpoint)
            storage.save_state(self.redis_storage)

    @staticmethod
    def get_str_date(time):
        return datetime.strptime(time, "%Y-%m-%d %H:%M:%S.%f")

    @backoff.on_exception(backoff.expo, Exception)
    @coroutine
    def transform_movie_data(self, target):
        """Трансформация данных выбранного направления (фильм, персона, жанр) в объект Movie."""
        while True:
            data: list = (yield)
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
                    self.set_person(movie.directors, person_data, person_id)
                elif line['role'] == 'actor':
                    self.set_person(movie.actors, person_data, person_id)
                elif line['role'] == 'writer':
                    self.set_person(movie.writers, person_data, person_id)
                genre_id = line.get('g_id')
                if not any(genre_id in p for p in movie.genres):
                    movie.genres += [{genre_id: line.get('g_name')}]
                movies.update({movie_id: movie})
            movies = [movie.dict(by_alias=True) for movie in movies.values()]
            target.send(movies)

    @staticmethod
    @backoff.on_exception(backoff.expo, Exception)
    def set_person(field, person_data: list, person_id) -> None:
        """Проверяет наличие персоны в объекте фильма."""
        if not any(person_id in p for p in field):
            field += person_data

    @backoff.on_exception(backoff.expo, Exception)
    @coroutine
    def load_data(self):
        """
        Загрузка в ES. Возвращает 409, если документ с таким айди уже существует.
        Принимает movie_data: Список словарей с фильмами, персонами и жанрами.
        """
        while True:
            movie_data: list = (yield)
            es_loader.load_to_es(movie_data, 'movies')


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
    @backoff.on_exception(backoff.expo, Exception)
    def __init__(self, connection):
        """
        1) Инициализация PostgreSQL.
        2) Обеспечения доступа к курсору из любого метода класса.
        """
        self.cr = connection.cursor(cursor_factory=RealDictCursor)

    @backoff.on_exception(backoff.expo, Exception)
    @coroutine
    def load_movie_ids_from_related_table(self, target, target_table_name, target_column_name):
        """Выгрузка айдишников фильмов, связанных с персонами,
         айди которых в ids и датой обновления из last_checkpoint."""
        while True:
            ids: tuple = (yield)
            last_checkpoint: datetime = (yield)
            if ids:
                movie_ids_query = f"""
                                SELECT m.id, m.modified
                                FROM content.movie m
                                LEFT JOIN content.{target_table_name} movie_rel ON movie_rel.movie_id = m.id
                                WHERE m.modified > '{last_checkpoint}' AND movie_rel.{target_column_name} IN {ids}
                                ORDER BY m.modified
                                LIMIT 100;
                                """
                self.cr.execute(movie_ids_query)
                movie_data = self.cr.fetchall()
                movie_ids = (m['id'] for m in movie_data)
                target.send(movie_ids)
            else:
                target.send([])

    @backoff.on_exception(backoff.expo, Exception)
    @coroutine
    def load_movie_data(self, target):
        """Выгрузка информации по фильмам, айди которых приходит в ids."""
        while True:
            ids: tuple = (yield)
            last_checkpoint: datetime = (yield)
            if not ids:
                target.send([])
            else:
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


if __name__ == "__main__":
    storage = RedisStorage(Redis(host="redis_db", decode_responses=True))
    # storage = RedisStorage(Redis(decode_responses=True))
    postgres_loader = PostgresLoader(psycopg2.connect(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password,
        options=f"-c search_path={db_scheme}"
    ))
    es_loader = ESLoader()
    etl = ETL()
    etl.start_etl_pipeline()
