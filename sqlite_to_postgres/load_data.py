import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from os import environ as env
from uuid import uuid4

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import cursor as _cr

load_dotenv()

db_host = env["db_host"]
db_port = env["db_port"]
db_name = env["db_name"]
db_user = env["db_user"]
db_password = env["db_password"]
db_scheme = env["db_scheme"]
db_path = env["db_path"]


def load_from_sqlite() -> None:
    """
    Основной метод загрузки данных из SQLite в Postgres.
    """
    postgres_saver = PostgresSaver()
    sqlite_loader = SQLiteLoader()

    data = sqlite_loader.load_movies()
    postgres_saver.save_all_data(data)


class PostgresSaver:
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
            options=f"-c search_path={db_scheme}",
        )
        self.cr = self.connection.cursor()

    def save_all_data(self, data: dict) -> None:
        """
        Сохранение информации из словаря по таблицам movie, genre, person, movie_genre_rel, movie_per в PostgreSQL.
        :param data: словарь с списками объектов.
        """
        cr = self.cr
        self.save_genres(cr, data)
        self.save_persons(cr, data)
        self.save_movies(cr, data)
        self.save_movie_person_rel(cr, data)
        self.save_movie_genre_rel(cr, data)
        self.connection.commit()
        self.connection.close()

    @staticmethod
    def save_genres(cr: _cr, data: dict) -> None:
        """
        Заполнение таблицы Жанров (genre) в PSQL.
        :param cr: курсор.
        :param data: словарь с общими данными для PSQL.
        """
        for genre_name in data["genre"]:
            genre = data["genre"][genre_name]
            query = f"insert into {db_name}.{db_scheme}.genre (id, name, created, modified) values (%s, %s, %s, %s); "
            cr.execute(query, (genre.id, genre.name, genre.created, genre.modified))

    @staticmethod
    def save_persons(cr: _cr, data: dict) -> None:
        """
        Заполнение таблицы Персон (person) в PSQL.
        :param cr: курсор.
        :param data: словарь с общими данными для PSQL.
        """
        for person_name in data["person"]:
            person = data["person"][person_name]
            query = f"insert into {db_name}.{db_scheme}.person (id, name, created, modified) values (%s, %s, %s, %s); "
            cr.execute(query, (person.id, person.name, person.created, person.modified))

    @staticmethod
    def save_movies(cr: _cr, data: dict) -> None:
        """
        Заполнение таблицы Фильмов (movie) в PSQL.
        :param cr: курсор.
        :param data: словарь с общими данными для PSQL.
        """
        for movie in data["movie"]:
            query = f"""insert into {db_name}.{db_scheme}.movie
                        (id, title, description, rating, created, modified)
                        values (%s, %s, %s, %s, %s, %s);"""
            cr.execute(
                query,
                (
                    movie.id,
                    movie.title,
                    movie.description,
                    movie.rating,
                    movie.created,
                    movie.modified,
                ),
            )

    @staticmethod
    def save_movie_person_rel(cr: _cr, data: dict) -> None:
        """
        Заполнение таблицы связи фильмов с персонами (movie_person_rel) в PSQL.
        :param cr: курсор.
        :param data: словарь с общими данными для PSQL.
        """
        for movie_person in data["movie_person_rel"]:
            query = f"""insert into {db_scheme}.movie_person_rel (id, movie_id, person_id, role, created, modified)
                        values (%s, %s, %s, %s, %s, %s)
                        on conflict (movie_id, person_id, role) do nothing;"""
            cr.execute(
                query,
                (
                    movie_person.id,
                    movie_person.movie_id,
                    movie_person.person_id,
                    movie_person.role,
                    movie_person.created,
                    movie_person.modified,
                ),
            )

    @staticmethod
    def save_movie_genre_rel(cr: _cr, data: dict) -> None:
        """
        Заполнение таблицы связи фильмов с жанрами (movie_genre_rel) в PSQL.
        :param cr: курсор.
        :param data: словарь с общими данными для PSQL.
        """
        for movie_genre in data["movie_genre_rel"]:
            query = f"""insert into {db_scheme}.movie_genre_rel (id, movie_id, genre_id, created, modified)
                        values (%s, %s, %s, %s, %s) on conflict (movie_id, genre_id) do nothing;"""
            cr.execute(
                query,
                (
                    movie_genre.id,
                    movie_genre.movie_id,
                    movie_genre.genre_id,
                    movie_genre.created,
                    movie_genre.modified,
                ),
            )


class SQLiteLoader:
    def __init__(self):
        """
        1) Инициализация подключения к SQLite.
        2) Предварительная корректировка БД.
        3) Создание переменных для хранения объектов Фильмов, Персон, Жанров и их связей.
        """
        self.conn = sqlite3.connect(db_path)
        self.fix_database()
        self.persons = {}
        self.genres = {}
        self.movie_genre_list = []
        self.movie_person_list = []
        self.movie_list = []

    def load_movies(self) -> dict:
        """
        Сбор данных из SQLite в Postgres.
        :return: словарь с данными для таблиц в PostgreSQL.
        """
        query = "select id, imdb_rating, genre, title, plot, director, writer, writers from movies"
        movies = self.conn.execute(query).fetchall()

        for movie in movies:
            new_movie = self.create_movie_obj(movie)
            self.create_persons_and_genres(new_movie)

        return dict(
            person=self.persons,
            genre=self.genres,
            movie_genre_rel=self.movie_genre_list,
            movie_person_rel=self.movie_person_list,
            movie=self.movie_list,
        )

    def create_movie_obj(self, movie: tuple):
        """
        Создание объекта фильма по информации, собранной из предоставленной БД.
        :param movie: tuple с информацией о фильме из SQLite.
        :return: объект фильма.
        """
        movie_id = movie[0]
        writer = movie[6]
        writers = movie[7]
        writer_data = self.get_writer_data(writer, writers)
        actor_data = self.get_actor_data(movie_id)
        new_movie = Movie(
            id=uuid4().hex,
            title=movie[3],
            description=movie[4],
            rating=movie[1],
            genres=movie[2].split(", "),
            directors=movie[5].split(","),
            actors=actor_data,
            writers=writer_data,
            created=datetime.now(),
            modified=datetime.now(),
        )
        self.movie_list.append(new_movie)
        return new_movie

    def create_persons_and_genres(self, movie) -> None:
        """
        Создание объектов Person и Genre.
        :param movie: UUID фильма.
        """
        movie_id = movie.id
        genres = movie.genres
        writers = movie.writers
        actors = movie.actors
        directors = movie.directors
        for genre in genres:
            self.create_genres(genre, movie_id)
        for director in directors:
            self.create_persons(movie_id, name=director, role="director")
        for writer in writers:
            self.create_persons(movie_id, name=writer["name"], role="writer")
        for actor in actors:
            self.create_persons(movie_id, name=actor["name"], role="actor")

    def create_genres(self, genre: str, movie_id) -> None:
        """
        Ищет жанр с данным названием в списке жанров либо создает новый объект Genre.
        :param genre: название жанра.
        :param movie_id: UUID фильма.
        """
        if genre not in self.genres:
            new_genre = Genre(
                id=uuid4().hex,
                name=genre,
                created=datetime.now(),
                modified=datetime.now(),
            )
            self.genres[genre] = new_genre
        else:
            new_genre = self.genres[genre]
        new_movie_genre = MovieGenre(
            id=uuid4().hex,
            movie_id=movie_id,
            genre_id=new_genre.id,
            created=datetime.now(),
            modified=datetime.now(),
        )
        self.movie_genre_list.append(new_movie_genre)

    def create_persons(self, movie_id, name: str, role: str) -> None:
        """
        Ищет человека с данным именем в списке людей либо создает новый объект Person.
        :param movie_id: UUID фильма.
        :param name: имя человека.
        :param role: роль человека.
        """
        if name not in self.persons:
            new_person = Person(
                id=uuid4().hex,
                name=name,
                created=datetime.now(),
                modified=datetime.now(),
            )
            self.persons[name] = new_person
        else:
            new_person = self.persons[name]
        new_movie_person = MoviePerson(
            id=uuid4().hex,
            movie_id=movie_id,
            person_id=new_person.id,
            role=role,
            created=datetime.now(),
            modified=datetime.now(),
        )
        self.movie_person_list.append(new_movie_person)

    def fix_database(self) -> None:
        """
        Метод для исправления проблемных моментов из БД, а именно:
        1) Удаляем дубликаты из movie_actors.
        2) Удаляем N/A записи из writers, actors.
        3) Заменяем значения столбцов director, plot с N/A на ''.
        4) Заменяем значения столбца на imdb_rating с N/A на 0.0.
        """
        conn = self.conn
        conn.execute("delete from writers where name = 'N/A'")
        conn.execute("delete from actors where name = 'N/A'")
        conn.execute("update movies set director = '' where director = 'N/A'")
        conn.execute("update movies set plot = '' where plot = 'N/A'")
        conn.execute("update movies set imdb_rating = 0.0 where imdb_rating = 'N/A'")
        conn.execute(
            """delete from movie_actors
                        where oid in (select min(OID)
                        from movie_actors
                        group by movie_id, actor_id
                        having count(*) > 1)"""
        )
        conn.commit()

    def get_writer_data(self, writer: str, writers: list) -> list:
        """
        Сбор информации о сценаристах из таблицы movies.
        :param writer: айди сценариста из колонки writer.
        :param writers: список с словарем [{'id': айди сценариста, 'name':  имя сценариста}] из колонки writers.
        :return: ([айдишники сценаристов], [имена сценаристов]).
        """

        def get_writer_ids(writer: str, writers: list) -> list:
            """
            Метод для сбора айдишников сценаристов из БД для конкретного фильма.
            :return: список с идентификаторами.
            """
            if writers:
                writer_ids = [writer.get("id") for writer in json.loads(writers)]
            else:
                writer_ids = [writer]
            return writer_ids

        writer_ids = get_writer_ids(writer, writers)
        writers_sql_info = []
        for writer_id in set(writer_ids):
            query = f"select id, name from writers where writers.id = '{writer_id}'"
            writers_sql_info.extend(self.conn.execute(query).fetchall())

        writers_list = []
        for writer in writers_sql_info:
            writers_list.append(dict(id=uuid4().hex, name=writer[1]))

        return writers_list

    def get_actor_data(self, movie_id: str) -> list:
        """
        :param movie_id: Идентификатор фильма.
        :return: ([айдишники актеров], [имена актеров]).
        """
        query = f"""select actors.id, actors.name from movie_actors inner join actors on actor_id=actors.id where
                    movie_id = '{movie_id}'"""
        actors = self.conn.execute(query).fetchall()
        actor_list = []
        for actor in actors:
            actor_list.append(dict(id=uuid4().hex, name=actor[1]))
        return actor_list


@dataclass(frozen=True)
class Genre:
    """
    Датакласс для записи информации о жанрах.
    """

    __slots__ = ["id", "name", "created", "modified"]

    id: str
    name: str
    created: datetime
    modified: datetime


@dataclass(frozen=True)
class Person:
    """
    Датакласс для записи информации о персонах.
    """

    __slots__ = ["id", "name", "created", "modified"]

    id: str
    name: str
    created: datetime
    modified: datetime


@dataclass(frozen=True)
class MoviePerson:
    """
    Датакласс для записи информации о связи фильмов и персон.
    """

    __slots__ = ["id", "movie_id", "person_id", "role", "created", "modified"]

    id: str
    movie_id: str
    person_id: str
    role: str
    created: datetime
    modified: datetime


@dataclass(frozen=True)
class MovieGenre:
    """
    Датакласс для записи информации о связи фильмов и жанров.
    """

    __slots__ = ["id", "movie_id", "genre_id", "created", "modified"]

    id: str
    movie_id: str
    genre_id: str
    created: datetime
    modified: datetime


@dataclass(frozen=True)
class Movie:
    """
    Датакласс для записи информации о фильме.
    """

    __slots__ = [
        "id",
        "title",
        "description",
        "rating",
        "genres",
        "directors",
        "actors",
        "writers",
        "created",
        "modified",
    ]

    id: str
    title: str
    description: str
    rating: float
    genres: list
    directors: list
    actors: list
    writers: list
    created: datetime
    modified: datetime


if __name__ == "__main__":
    load_from_sqlite()
