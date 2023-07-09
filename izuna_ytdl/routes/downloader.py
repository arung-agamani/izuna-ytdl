from flask import Blueprint, request, make_response, current_app
from cerberus import Validator
import yt_dlp
import json
import re
import threading
from typing import cast
from redis import Redis
from ..utils import regexes, responses
from ..utils.models import *

bp = Blueprint("downloader", __name__, url_prefix="/api/downloader")

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
    dl_info = get_download_info(id, redis)
    # TODO: investigate possible errors
    if dl_info is not None:
        res = make_response()
        data = {"status": True,
                "message": f"{dl_info.message}",
                }
        return responses.json_res(res, data)
    # else:
    #     import pprint
    #     pprint.pprint(json.dumps(dl_info))
    set_download_info(DownloadInfo(id, DownloadStatus.QUEUED,
                      "Item is being downloaded"), redis)
    res = make_response()
    data = {
        "success": True,
        "message": f"Queuing download task for Youtube video with id {id}"
    }
    # threading part
    if dl_info is None:
        x = threading.Thread(target=download, args=(id, redis))
        x.start()
    return responses.json_res(res, data, 202)

# TODO: add garbage collection.
ydl_opts = {
    'format': 'm4a/bestaudio/best',
    'outtmpl': {'default': '%(title)s.%(ext)s'},
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
    }]
}


def download(id: str, r: Redis):
    # TODO: handle errors properly. save error message in redis
    # TODO: upload to s3, save url in question to redis

    try:
        ydl_opts = {
            'format': 'm4a/bestaudio/best',
            'outtmpl': {'default': '%(title)s.%(ext)s'},
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }]
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={id}", download=False)
            # print(json.dumps(ydl.sanitize_info(info)))
            duration = info.get("duration")
            if duration > 600:
                set_download_info(DownloadInfo(
                    id,
                    DownloadStatus.DELETED,
                    "Duration too long (over 10 minutes)"
                ), r)
                return
            set_download_status(id, DownloadStatus.DOWNLOADING, r)
            count = ydl.download(f"https://www.youtube.com/watch?v={id}")
            set_download_info(DownloadInfo(
                id, DownloadStatus.DOWNLOADED,
                f"Item downloaded for id ${id}"
            ), r)
            return
    except yt_dlp.utils.DownloadError as err:
        print("Something went wrong")
        print(err)
        set_download_info(DownloadInfo(
            id,
            DownloadStatus.DELETED,
            f"Error: {err}"
        ), r)
