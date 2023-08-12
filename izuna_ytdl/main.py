import flask
from flask import current_app
from datetime import timedelta
from redis_om import Migrator, get_redis_connection
from flask_jwt_extended import JWTManager
from . import config


def create_app(config_filename="") -> flask.Flask:
    app = flask.Flask(__name__)
    if (config_filename != ""):
        app.config.from_pyfile(config_filename)
    app.secret_key = config.KAKUSU_HIMITSU
    app.config['JWT_SECRET_KEY'] = config.JWT_NO_HIMITSU
    app.config['JWT_TOKEN_LOCATION'] = "cookies"
    app.config['JWT_COOKIE_SECURE'] = False
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=12)

    Migrator(module="izuna_ytdl.models").run()
    redis_client = get_redis_connection()
    redis_client.set("foo", "bar")
    assert redis_client.get("foo") == "bar"
    redis_client.delete("foo")

    # JWT Manager
    jwt = JWTManager(app)

    with app.app_context():
        current_app.redis = redis_client
        current_app.jwt = jwt

    from .routes import downloader, user
    app.register_blueprint(downloader.bp)
    app.register_blueprint(user.bp)

    return app
