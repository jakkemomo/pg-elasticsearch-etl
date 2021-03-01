from datetime import datetime
from functools import wraps
from typing import Coroutine

import backoff
from psycopg2.extras import RealDictCursor


def coroutine(func):
    @wraps(func)
    def inner(*args, **kwargs):
        fn = func(*args, **kwargs)
        next(fn)
        return fn

    return inner


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
    def get_movie_ids(
        self, target: Coroutine, target_table_name, target_column_name
    ) -> Coroutine:
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
                                ORDER BY m.modified;
                                """
                self.cr.execute(movie_ids_query)
                movie_data = self.cr.fetchall()
                movie_ids = (m["id"] for m in movie_data)
                target.send(tuple(movie_ids))
                target.send(last_checkpoint)
            else:
                target.send([])
                target.send(last_checkpoint)

    @backoff.on_exception(backoff.expo, Exception)
    @coroutine
    def load_movie_data(self, target: Coroutine) -> Coroutine:
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
                                    m.auth_required,
                                    movie_person.role as role,
                                    p.id as p_id,
                                    p.name as p_name,
                                    p.created as p_created,
                                    p.modified as p_modified,
                                    g.id as g_id,
                                    g.name as g_name,
                                    g.description as g_description,
                                    g.created as g_created,
                                    g.modified as g_modified
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
