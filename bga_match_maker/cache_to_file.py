import os
import time
import json
import logging
from functools import wraps

one_week = 604800
logger = logging.getLogger(__name__)


def cache_to_file(key: str, func, *args, **kwargs):
    return cache(key)(func)(*args, **kwargs)


def cache(key: str, cache_duration: int = one_week):
    filename = key+".json"

    def read():
        if not os.path.exists(filename):
            raise Exception(f"{filename} does not exist")

        with open(filename, "r") as file:
            logger.debug(f"Loading ${key=} from cache")
            return json.load(file)

    def write(content):
        with open(filename, "w") as file:
            logger.debug(f"Writing ${key=} to cache")
            json.dump(content, file , indent=2)

    def decorator(f):

        @wraps(f)
        def replacement(*args, **kwargs):
            if os.path.exists(filename) and time.time() - cache_duration < os.path.getmtime(filename):
                return read()
            else:
                try:
                    result = f(*args, **kwargs)
                    write(result)
                    return result
                except Exception:
                    logger.warning(f"Could not fetch a new version of cache ${key=}")
                    return read()

        return replacement

    return decorator
