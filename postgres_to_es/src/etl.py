import logging
import backoff

from functools import wraps
from typing import List, Optional, Dict, Coroutine
from pydantic import BaseModel
from time import sleep
from postgres_to_es.src.settings import DEFAULT_SLEEP_TIME, DEFAULT_DATE

_logger = logging.getLogger(__name__)


def coroutine(func):
    @wraps(func)
    def inner(*args, **kwargs):
        fn = func(*args, **kwargs)
        next(fn)
        return fn

    return inner


class ETL:
    def __init__(self, storage, db_loader, es_loader):
        self.storage = storage
        self.state = storage.retrieve_state()
        self.db_loader = db_loader
        self.es_loader = es_loader
        self.current_table = ''

    @backoff.on_exception(backoff.expo, Exception)
    def start_etl_pipeline(self) -> None:
        """
        Последовательная загрузка фильмов, жанров и персон из постгреса в ES.
        Раз в sleep_time секунд запускает etl процесс с нуля.
        """
        loader = self.loader()
        transformer = self.transform_movie_data(loader)
        movie_merger = self.db_loader.load_movie_data(transformer)
        movie_producer = self.get_ids_for_update(movie_merger)
        genre_producer = self.get_ids_for_update(self.db_loader.get_movie_ids(
            movie_merger, 'movie_genre_rel', 'genre_id')
        )
        person_producer = self.get_ids_for_update(self.db_loader.get_movie_ids(
            movie_merger, 'movie_person_rel', 'person_id')
        )
        
        while True:
            _logger.info("Movie loading started")
            self.current_table = 'movie'
            movie_producer.send('movie')

            _logger.info("Movies from updated genres are loading")
            self.current_table = 'genre'
            genre_producer.send('genre')

            _logger.info("Movies from updated persons are loading")
            self.current_table = 'person'
            person_producer.send('person')

            sleep(DEFAULT_SLEEP_TIME)

    @backoff.on_exception(backoff.expo, Exception)
    @coroutine
    def get_ids_for_update(self, target: Coroutine) -> Coroutine:
        """
        Выгрузка айдишников из БД для выбранного направления (фильм, персона, жанр).
        table_name: назывние таблицы
        last_checkpoint: самый последний modified для выбранного направления.
        storage_data: словарь данного направления из локального хранилища.
        :return: айдишники данного направления для обновления, last_checkpoint.
        """

        while True:
            table_name: str = (yield)
            last_checkpoint = self.state.get(
                f"{table_name}_last_modified",
                DEFAULT_DATE
            )
            query = """
                    SELECT id, modified
                    FROM content.%s
                    WHERE modified > '%s'
                    ORDER BY modified
                    LIMIT 100;
                """ % (table_name, last_checkpoint)
            self.db_loader.cr.execute(query)
            object_ids = self.db_loader.cr.fetchall()
            ids_for_update = []
            for obj in object_ids:
                object_id = obj.get('id')
                modified = obj.get('modified').strftime("%Y-%m-%d %H:%M:%S.%f")
                if last_checkpoint < modified:
                    ids_for_update.append(object_id)
                    self.state.update({f"{table_name}_last_modified": modified})
            target.send(tuple(ids_for_update))
            target.send(last_checkpoint)
            self.storage.save_state(self.state)

    @backoff.on_exception(backoff.expo, Exception)
    @coroutine
    def transform_movie_data(self, target: Coroutine) -> Coroutine:
        """Трансформация данных выбранного направления (фильм, персона, жанр) в объект Movie."""
        while True:
            data: list = (yield)
            movies = {}
            persons = {}
            genres = {}
            for line in data:
                movie_id = line['m_id']
                movie_name = line['title']
                movie_data = dict(
                    id=movie_id,
                    title=movie_name,
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
                person_role = line['role']

                if person_role == 'director':
                    self.set_person(movie.directors, person_data, person_id)
                elif person_role == 'actor':
                    self.set_person(movie.actors, person_data, person_id)
                elif person_role == 'writer':
                    self.set_person(movie.writers, person_data, person_id)

                if self.current_table == 'person':
                    person = persons.get(person_id)
                    if not person:
                        person_created = line.get('p_created')
                        person_modified = line.get('p_modified')
                        person = Person(id=person_id, full_name=person_name, roles=[person_role],
                                        movies=[{movie_id: movie_name}],
                                        created=person_created.strftime("%Y-%m-%d %H:%M:%S.%f"),
                                        modified=person_modified.strftime("%Y-%m-%d %H:%M:%S.%f"))
                        persons.update({person_id: person})
                    else:
                        existing_roles = persons[person_id].roles
                        if person_role not in existing_roles:
                            existing_roles.append(person_role)
                        existing_movies = persons[person_id].movies
                        if not next((item for item in existing_movies if item.get(movie_id)), None):
                            existing_movies.append({movie_id: movie_name})

                genre_id = line.get('g_id')
                genre_name = line.get('g_name')
                if not any(genre_id in p for p in movie.genres):
                    movie.genres += [{genre_id: genre_name}]

                if self.current_table == 'genre':
                    genre_description = line.get('g_description')
                    genre_created = line.get('g_created')
                    genre_modified = line.get('g_modified')
                    genre = genres.get(genre_id)
                    if not genre:
                        # создаем новый объект жанра
                        genre = Genre(id=genre_id, name=genre_name, description=genre_description,
                                      movies=[{movie_id: movie_name}],
                                      created=genre_created.strftime("%Y-%m-%d %H:%M:%S.%f"),
                                      modified=genre_modified.strftime("%Y-%m-%d %H:%M:%S.%f"))
                        genres.update({genre_id: genre})
                    else:
                        existing_movies = genres[genre_id].movies
                        if not next((item for item in existing_movies if item.get(movie_id)), None):
                            existing_movies.append({movie_id: movie_name})

                movies.update({movie_id: movie})
            movies = [movie.dict(by_alias=True) for movie in movies.values()]
            genres = [genre.dict(by_alias=True) for genre in genres.values()]
            persons = [person.dict(by_alias=True) for person in persons.values()]
            target.send(movies)
            target.send(genres)
            target.send(persons)

    @staticmethod
    @backoff.on_exception(backoff.expo, Exception)
    def set_person(person_list_ids: List[Dict[str, str]], person_data: list, person_id: str) -> None:
        """Проверяет наличие персоны в объекте фильма."""
        if not any(person_id in p for p in person_list_ids):
            person_list_ids += person_data

    @backoff.on_exception(backoff.expo, Exception)
    @coroutine
    def loader(self) -> Coroutine:
        """
        Загрузка в ES. Возвращает 409, если документ с таким айди уже существует.
        Принимает movie_data: Список словарей с фильмами, персонами и жанрами.
        """
        while True:
            movie_data: list = (yield)
            genre_data: list = (yield)
            person_data: list = (yield)
            self.es_loader.load_to_es(movie_data, 'movies')
            self.es_loader.load_to_es(genre_data, 'genres')
            self.es_loader.load_to_es(person_data, 'persons')


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


class Genre(BaseModel):
    """Схема для загрузки жанров."""

    id: str
    name: str
    description: Optional[str] = ''
    movies: Optional[List[Dict[str, str]]] = []
    created: str
    modified: str


class Person(BaseModel):
    """Схема для загрузки персон."""

    id: str
    full_name: str
    movies: Optional[List[Dict[str, str]]] = []
    roles: Optional[List[str]] = ''
    created: str
    modified: str
