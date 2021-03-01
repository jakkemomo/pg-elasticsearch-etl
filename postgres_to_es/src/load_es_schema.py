import logging

from elasticsearch import Elasticsearch

from postgres_to_es.src.settings import (
    BASE_ES_URL,
    DEFAULT_GENRE_ES_SCHEMA,
    DEFAULT_GENRE_INDEX_NAME,
    DEFAULT_MOVIE_ES_SCHEMA,
    DEFAULT_MOVIE_INDEX_NAME,
    DEFAULT_PERSON_ES_SCHEMA,
    DEFAULT_PERSON_INDEX_NAME,
)

_logger = logging.getLogger(__name__)

elastic = Elasticsearch(hosts=BASE_ES_URL)

response = elastic.indices.create(
    index=DEFAULT_MOVIE_INDEX_NAME, body=DEFAULT_MOVIE_ES_SCHEMA, ignore=400
)

_logger.info(response)

response = elastic.indices.create(
    index=DEFAULT_GENRE_INDEX_NAME, body=DEFAULT_GENRE_ES_SCHEMA, ignore=400
)

_logger.info(response)

response = elastic.indices.create(
    index=DEFAULT_PERSON_INDEX_NAME, body=DEFAULT_PERSON_ES_SCHEMA, ignore=400
)

_logger.info(response)
