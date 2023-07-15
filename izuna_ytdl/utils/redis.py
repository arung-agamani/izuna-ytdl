import redis
import os

redis_connection = None


def get_connection():
    global redis_connection
    REDIS_HOST = os.environ.get("REDIS_HOST")
    if REDIS_HOST is None:
        REDIS_HOST = "localhost"
    if redis_connection is None:
        redis_connection = redis.Redis(
            host=REDIS_HOST, port="6379", password="eYVX7EwVmmxKPCDmwMtyKVge8oLd2t81", decode_responses=True, )
    return redis_connection
