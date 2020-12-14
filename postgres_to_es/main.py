import logging
import psycopg2

from postgres_to_es.src.storage import RedisStorage, Redis
from postgres_to_es.src.es_loader import ESLoader
from postgres_to_es.src.settings import DB_HOST, DB_NAME, DB_PORT, DB_USER, DB_SCHEME, DB_PASSWORD, BASE_REDIS_HOST
from postgres_to_es.src.etl import ETL
from postgres_to_es.src.postgres_loader import PostgresLoader

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    storage = RedisStorage(Redis(host=BASE_REDIS_HOST, decode_responses=True))
    postgres_loader = PostgresLoader(psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        options=f"-c search_path={DB_SCHEME}"
    ))
    es_loader = ESLoader()
    etl = ETL(storage, postgres_loader, es_loader)
    logging.info("ETL PROCESS STARTED")
    etl.start_etl_pipeline()
