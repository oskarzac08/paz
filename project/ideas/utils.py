import secrets
from django.core.cache import cache

CODE_TTL_SECONDS = 10 * 60  # 10 minutes


def generate_code(length: int = 6) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def cache_key(email: str) -> str:
    return f"email_verification_code:{email.lower().strip()}"


def store_code(email: str, code: str) -> None:
    cache.set(cache_key(email), code, timeout=CODE_TTL_SECONDS)


def verify_code(email: str, code: str) -> bool:
    saved = cache.get(cache_key(email))
    if not saved:
        return False
    ok = secrets.compare_digest(saved, code.strip())
    if ok:
        cache.delete(cache_key(email))
    return ok
