import redis


def is_redis_available(url: str, timeout_seconds: float = 1.0) -> bool:
    """
    Quick connectivity check for local dev.
    Celery/RQ rely on Redis; if Redis isn't reachable, we can fall back to
    synchronous execution in the API to keep the product usable.
    """
    try:
        r = redis.Redis.from_url(
            url,
            socket_connect_timeout=timeout_seconds,
            socket_timeout=timeout_seconds,
            decode_responses=True,
        )
        r.ping()
        return True
    except Exception:
        return False

