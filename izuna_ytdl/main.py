import json
# import yt_dlp
import re
import flask
from flask import current_app
import redis


URL = 'https://www.youtube.com/watch?v=ICNpuzVc4l8'
valid_yt_url_regex = "(youtu.*be.*)\/(watch\?v=|embed\/|v|shorts|)(.*?((?=[&#?])|$))"
# with yt_dlp.YoutubeDL({}) as ydl:
#     info = ydl.extract_info(URL, download=False)
#     # print(json.dumps(ydl.sanitize_info(info)))
#     duration = info.get("duration")
#     if (duration > 600):
#         print
#     print(duration)

# res = re.search(valid_yt_url_regex, URL)
# print(res.groups()[2])


def create_app(config_filename="") -> flask.Flask:
    app = flask.Flask(__name__)
    if (config_filename != ""):
        app.config.from_pyfile(config_filename)

    redis_client = redis.Redis(
        host="localhost", port="6379", password="eYVX7EwVmmxKPCDmwMtyKVge8oLd2t81")
    redis_client.set("foo", "bar")
    assert redis_client.get("foo") == b"bar"
    redis_client.delete("foo")

    with app.app_context():
        current_app.redis = redis_client

    from .routes import downloader
    app.register_blueprint(downloader.bp)

    return app
