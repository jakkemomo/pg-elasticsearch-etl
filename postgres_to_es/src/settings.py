from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from os import environ as env

load_dotenv()

DB_HOST: str = env["db_host"]
DB_PORT: str = env["db_port"]
DB_NAME: str = env["db_name"]
DB_USER: str = env["db_user"]
DB_PASSWORD: str = env["db_password"]
DB_SCHEME: str = env["db_scheme"]
DEFAULT_SLEEP_TIME: int = 5
DEFAULT_INDEX_NAME: Optional[str] = "movies"
DEFAULT_DATE: str = datetime(day=1, month=1, year=1980).strftime("%Y-%m-%d %H:%M:%S.%f")
BASE_ES_URL: str = "http://127.0.0.1:9200/"
# BASE_ES_URL: str = "http://elasticsearch:9200/"
ES_SCHEMA_FILENAME: str = env.get('elastic_schema') or 'schema.json'
DEFAULT_ES_SCHEMA = schema = {
    "settings": {
        "refresh_interval": "1s",
        "analysis": {
            "filter": {
                "english_stop": {
                    "type": "stop",
                    "stopwords": "_english_"
                },
                "english_stemmer": {
                    "type": "stemmer",
                    "language": "english"
                },
                "english_possessive_stemmer": {
                    "type": "stemmer",
                    "language": "possessive_english"
                },
                "russian_stop": {
                    "type": "stop",
                    "stopwords": "_russian_"
                },
                "russian_stemmer": {
                    "type": "stemmer",
                    "language": "russian"
                }
            },
            "analyzer": {
                "ru_en": {
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "english_stop",
                        "english_stemmer",
                        "english_possessive_stemmer",
                        "russian_stop",
                        "russian_stemmer"
                    ]
                }
            }
        }
    },
    "mappings": {
        "dynamic": "strict",
        "properties": {
            "id": {
                "type": "keyword"
            },
            "title": {
                "type": "text",
                "analyzer": "ru_en",
                "fields": {
                    "raw": {
                        "type": "keyword"
                    }
                }
            },
            "description": {
                "type": "text",
                "analyzer": "ru_en"
            },
            "imdb_rating": {
                "type": "float"
            },
            "type": {
                "type": "text",
                "analyzer": "ru_en"
            },
            "created": {
                "type": "date",
                "format": "YYYY-MM-DD HH:mm:ss.SSSSSS"
            },
            "modified": {
                "type": "date",
                "format": "YYYY-MM-DD HH:mm:ss.SSSSSS"
            },
            "genres": {
                "type": "nested",
                "dynamic": "false",
                "properties": {
                    "id": {
                        "type": "keyword"
                    },
                    "name": {
                        "type": "text",
                        "analyzer": "ru_en"
                    }
                }
            },
            "actors": {
                "type": "nested",
                "dynamic": "false",
                "properties": {
                    "id": {
                        "type": "keyword"
                    },
                    "name": {
                        "type": "text",
                        "analyzer": "ru_en"
                    }
                }
            },
            "writers": {
                "type": "nested",
                "dynamic": "false",
                "properties": {
                    "id": {
                        "type": "keyword"
                    },
                    "name": {
                        "type": "text",
                        "analyzer": "ru_en"
                    }
                }
            },
            "directors": {
                "type": "nested",
                "dynamic": "false",
                "properties": {
                    "id": {
                        "type": "keyword"
                    },
                    "name": {
                        "type": "text",
                        "analyzer": "ru_en"
                    }
                }
            }
        }
    }
}