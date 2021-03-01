from json import dumps, loads

import backoff
from redis import Redis


class RedisStorage:
    def __init__(self, redis_adapter: Redis):
        self.redis_adapter = redis_adapter

    @backoff.on_exception(backoff.expo, Exception)
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
        self.redis_adapter.set("data", dumps(state))

    @backoff.on_exception(backoff.expo, Exception)
    def retrieve_state(self) -> dict:
        """Получение сохренных данных из Редиса в виде словаря."""
        raw_data = self.redis_adapter.get("data")
        if raw_data is None:
            return {}
        return loads(raw_data)
