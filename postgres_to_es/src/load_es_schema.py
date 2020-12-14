import logging
from elasticsearch import Elasticsearch
from postgres_to_es.src.settings import DEFAULT_ES_SCHEMA, BASE_ES_URL, DEFAULT_INDEX_NAME

_logger = logging.getLogger(__name__)

elastic = Elasticsearch(hosts=BASE_ES_URL)

elastic.indices.delete(index=DEFAULT_INDEX_NAME, ignore=[400, 404])

response = elastic.indices.create(
    index=DEFAULT_INDEX_NAME,
    body=DEFAULT_ES_SCHEMA,
    ignore=400
)

_logger.info(response)
