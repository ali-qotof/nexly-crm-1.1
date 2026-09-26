"""
Rate limiting بسيط لمحاولات تسجيل الدخول (القاعدة 38).

ملاحظة صريحة: هذا التنفيذ في-الذاكرة (in-process) ومناسب لعملية Uvicorn واحدة. إذا تم تشغيل
أكثر من Worker/Instance في الإنتاج، يجب استبداله بمخزن مشترك (Redis) — هذا موثّق كقيد معروف
وليس إخفاءً للمشكلة.
"""
import time
from collections import defaultdict

_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300  # 5 دقائق

_attempts: dict[str, list[float]] = defaultdict(list)


def is_rate_limited(identifier: str) -> bool:
    now = time.time()
    window_start = now - _WINDOW_SECONDS
    _attempts[identifier] = [t for t in _attempts[identifier] if t > window_start]
    return len(_attempts[identifier]) >= _MAX_ATTEMPTS


def register_failed_attempt(identifier: str) -> None:
    _attempts[identifier].append(time.time())


def clear_attempts(identifier: str) -> None:
    _attempts.pop(identifier, None)
