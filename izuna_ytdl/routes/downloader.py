from flask import Blueprint, request, make_response, current_app, jsonify
from flask import Response
from cerberus import Validator
import yt_dlp
import json
import re
import threading
from ..utils import regexes, responses
from ..models.download_task import *
from flask_jwt_extended import (
    jwt_required, get_jwt_identity, get_jwt,
    create_access_token, set_access_cookies,
)
from datetime import (
    datetime, timedelta, timezone
)
import boto3
from botocore.exceptions import ClientError
import os
import logging
from .. import config

s3 = boto3.client('s3')


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


@bp.after_request
def refresh_jwt(response: Response):
    try:
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
        # print(exp_timestamp)
        # print(now)
        # print(target_timestamp)
        if target_timestamp > exp_timestamp:
            logging.debug("Expiring. Refreshing...")
            logging.debug(target_timestamp - exp_timestamp)
            access_token = create_access_token(
                identity=get_jwt_identity())
            set_access_cookies(response, access_token)
        return response
    except (RuntimeError, KeyError):
        # Case where there is not a valid JWT. Just return the original response
        return response


@bp.route("/info", methods=['GET'])
@jwt_required()
def get_info():
    username = get_jwt_identity()
    tasks = DownloadTask.find(DownloadTask.created_by == username).all()
    list_obj = [json.loads(x.json()) for x in tasks]
    response = jsonify({
        "success": True,
        "data": list_obj
    })

    return response


@bp.route("/retrieve", methods=['GET'])
@jwt_required()
def retrieve_s3_file():
    args = request.args

    id = args.get('id')

    validator = Validator(get_info_schema)
    validate_payload = {
        "id": id
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
    task = get_task(validate_payload['id'])
    if task is None:
        response = jsonify({
            "success": False,
            "message": "Not found"
        })
        return response, 404
    try:
        res = s3.generate_presigned_url('get_object',
                                        Params={
                                            'Bucket': config.BUCKET_NAME,
                                            'Key': f"public/{task.title}"
                                        },
                                        ExpiresIn=600
                                        )
        return res
    except ClientError as e:
        logging.error("Client error")
        logging.error(e)
        return jsonify({
            "success": False,
            "message": "Something went wrong"
        }), 500


@bp.route("/download", methods=["POST"])
@jwt_required()
async def handle_download():
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
    task = get_task(id)
    res = make_response()
    data = {
        "success": True,
        "message": f"Queuing download task for Youtube video with id {id}"
    }
    username = get_jwt_identity()
    # threading part
    if task is None:
        logging.debug("No task found. Creating and queueing")
        _task = create_task(
            id=id, url=validate_payload['url'], title="", created_by=username)
        x = threading.Thread(target=download, args=(id, _task))
        x.start()
    else:
        logging.debug("Existing task found. Checking")
        if task.state == QUEUED:
            logging.debug("Existing task found and queued. Executing")
            x = threading.Thread(target=download, args=(id, task))
            x.start()
        elif task.state == DONE:
            return jsonify({
                "success": True,
                "message": "Data has already been downloaded."
            })
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


def download(id: str, task: DownloadTask):
    final_filename = None
    final_filepath = ""

    def yt_dlp_monitor(d):
        nonlocal final_filename
        nonlocal final_filepath
        if d.get('status') == 'finished':
            final_filename = d.get('info_dict').get('filepath')
            final_filepath = d.get('info_dict').get(
                "__files_to_move").get(final_filename)
    try:

        ydl_opts = {
            'format': 'm4a/bestaudio/best',
            'outtmpl': {'default': '%(title)s.%(ext)s'},
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
            'postprocessor_hooks': [yt_dlp_monitor]
        }
        task.update_state(PROCESSING)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={id}", download=False)
            duration = info.get("duration")
            if duration > 600:
                task.update_state(ERROR_TOO_LONG)
                return

            count = ydl.download(f"https://www.youtube.com/watch?v={id}")
            logging.debug("Download complete")
            logging.debug(f"End filename: ${final_filename}")
            logging.debug(f"End filepath: ${final_filepath}")
            s3.upload_file(final_filepath, config.BUCKET_NAME,
                           f"public/{final_filename}")
            task.update(final_filename, DONE)
            os.remove(final_filepath)
            return
    except yt_dlp.utils.DownloadError as err:
        logging.error("Download error")
        logging.error(err)
        task.update_state(ERROR_UNKNOWN)
    except:
        logging.error("Other errors")
        task.update_state(ERROR_UNKNOWN)
