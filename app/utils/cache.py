import json
from typing import Any, Optional

import redis

from app.core.config import settings


_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def get_json_cache(key: str) -> Optional[Any]:
    try:
        r = get_redis_client()
        raw = r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        return None


def set_json_cache(key: str, value: Any, ttl_seconds: int = 60) -> None:
    try:
        r = get_redis_client()
        r.setex(key, ttl_seconds, json.dumps(value))
    except Exception:
        # Cache is an optimization; failures should not break core flows.
        return

