from typing import Optional

class Cache:
    def __init__(self):
        self._cache = {}

    def get(self, date_str: str) -> Optional[list]:
        key = date_str
        return self._cache.get(key)

    def set(self, date_str: str, data: list):
        key = date_str
        self._cache[key] = data

memory_cache = Cache() 