import logging

from elasticsearch import Elasticsearch
from postgres_to_es.src.settings import DEFAULT_ES_SCHEMA

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

# elastic = Elasticsearch(hosts='elasticsearch')
elastic = Elasticsearch(hosts='localhost:9200')

elastic.indices.delete(index='movies', ignore=[400, 404])

response = elastic.indices.create(
    index="movies",
    body=DEFAULT_ES_SCHEMA,
    ignore=400
)

_logger.info(response)
