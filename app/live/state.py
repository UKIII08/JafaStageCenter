# Stan pokoju LIVE per wspólnota (bieżący slajd itd.).
# Prod: Redis (przeżywa restart workera, działa przy wielu workerach);
# dev/test: pamięć procesu. Jeden aktywny pokój na wspólnotę (PLAN §3.3).
import json
import os

_memory = {}
_redis = None
if os.environ.get('REDIS_URL') and not os.environ.get('JAFA_NO_REDIS'):
    try:
        import redis as _redis_mod
        _redis = _redis_mod.from_url(os.environ['REDIS_URL'],
                                     socket_connect_timeout=2)
        _redis.ping()
    except Exception:
        _redis = None


def _key(church_id):
    return f'live:state:{church_id}'


def set_state(church_id, state):
    if _redis:
        _redis.set(_key(church_id), json.dumps(state), ex=60 * 60 * 12)
    else:
        _memory[church_id] = state


def get_state(church_id):
    if _redis:
        raw = _redis.get(_key(church_id))
        return json.loads(raw) if raw else None
    return _memory.get(church_id)


def clear_state(church_id):
    if _redis:
        _redis.delete(_key(church_id))
    else:
        _memory.pop(church_id, None)
