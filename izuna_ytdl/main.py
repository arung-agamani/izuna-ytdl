import flask
from flask import current_app
import redis
import os


def create_app(config_filename="") -> flask.Flask:
    app = flask.Flask(__name__)
    if (config_filename != ""):
        app.config.from_pyfile(config_filename)

    REDIS_HOST = os.environ.get("REDIS_HOST")
    if REDIS_HOST is None:
        REDIS_HOST = "localhost"
    redis_client = redis.Redis(
        host=REDIS_HOST, port="6379", password="eYVX7EwVmmxKPCDmwMtyKVge8oLd2t81", decode_responses=True, )
    redis_client.set("foo", "bar")
    assert redis_client.get("foo") == "bar"
    redis_client.delete("foo")

    with app.app_context():
        current_app.redis = redis_client

    from .routes import downloader
    app.register_blueprint(downloader.bp)

    return app
