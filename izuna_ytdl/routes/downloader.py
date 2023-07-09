from flask import Blueprint, request, make_response, current_app
from cerberus import Validator
import yt_dlp
from ..utils import regexes, responses
import json
import re
import threading
from typing import cast
from redis import Redis
from time import sleep


bp = Blueprint("downloader", __name__, url_prefix="/downloader")


get_info_schema = {
    'id': {'type': 'string'}
}
download_schema = {
    'url': {
        'type': 'string',
        'regex': regexes.YOUTUBE_URL
    }
}


@bp.route("/info", methods=['GET'])
def get_info():
    args = request.args
    id = args.get("id")

    validator = Validator()
    validate_payload = {
        "id": id
    }
    is_valid = validator.validate(validate_payload, get_info_schema)
    if is_valid is False:
        response = make_response()
        response.status_code = 400
        response.data = json.dumps({
            "success": False,
            "message": "validation error",
            "errors": validator.errors
        })
        response.content_type = "application/json"
        return response

    response = make_response()
    response.data = f"You are searching for {id}"
    response.content_type = "text/plain"

    return response


@bp.route("/download", methods=["POST"])
async def download():
    body = request.json

    validator = Validator(download_schema)
    validate_payload = {
        "url": body.get("url")
    }
    is_valid = validator.validate(validate_payload)
    if is_valid is False:
        response = make_response()
        response.status_code = 400
        response.data = json.dumps({
            "success": False,
            "message": "validation error",
            "errors": validator.errors
        })
        response.content_type = "application/json"
        return response

    re_match = re.match(regexes.YOUTUBE_URL, validate_payload["url"])
    id = re_match.groups()[4]
    redis = cast(Redis, current_app.redis)
    state = redis.get(id)
    # TODO: return status properly (202 and 200) with error
    # TODO: define state machine for the download task
    if state is not None:
        res = make_response()
        data = {
            "success": True,
            "message": f"Task for id {id} is in pending state",
            "state": str(state)
        }
        return responses.json_res(res, data)
    redis.set(id, "QUEUED")
    res = make_response()
    data = {
        "success": True,
        "message": f"Queuing download task for Youtube video with id {id}"
    }
    # threading part
    x = threading.Thread(target=download, args=(id, redis))
    x.start()
    return responses.json_res(res, data)


def dispatch_task(id: str, r: Redis):
    sleep(10)
    r.delete(id)
    print(f"Task for id {id} is done")


def download(id: str, r: Redis):
    # TODO: handle errors properly. save error message in redis
    # TODO: upload to s3, save url in question to redis
    try:
        with yt_dlp.YoutubeDL({}) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={id}", download=False)
            # print(json.dumps(ydl.sanitize_info(info)))
            duration = info.get("duration")
            print(duration)
            r.set(id, "DOWNLOADED")
    except yt_dlp.utils.DownloadError as err:
        print("Something went wrong")
        print(err)
        r.set(id, "ERROR")
