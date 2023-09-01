from flask import (
    Blueprint,
    request,
    current_app,
    make_response,
    session,
    jsonify,
    Response,
)
import json
from cerberus import Validator
from ..utils import regexes, responses, models
from ..models.user import get_user, create_user, User
from ...izuna_ytdl.config import DOMAIN, MASTER_SIGNUP_CODE
from redis_om import RedisModel
from flask_jwt_extended import (
    set_access_cookies,
    create_access_token,
    jwt_required,
    unset_access_cookies,
)
from flask_jwt_extended import get_jwt, get_jwt_identity
from datetime import datetime, timezone, timedelta
import logging

bp = Blueprint("user", __name__, url_prefix="/api/user")

signup_schema = {
    "username": {"type": "string", "regex": regexes.USERNAME},
    "password": {"type": "string", "minlength": 8, "regex": regexes.PASSWORD},
    "signup_code": {"type": "string", "regex": regexes.SIGNUP},
}

signin_schema = {
    "username": {"type": "string", "regex": regexes.USERNAME},
    "password": {"type": "string", "minlength": 8, "regex": regexes.PASSWORD},
}


# @bp.after_request
# def refresh_jwt(response: Response):
#     try:
#         exp_timestamp = get_jwt()["exp"]
#         now = datetime.now(timezone.utc)
#         target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
#         # print(exp_timestamp)
#         # print(now)
#         # print(target_timestamp)
#         if target_timestamp > exp_timestamp:
#             logging.debug("Expiring. Refreshing...")
#             logging.debug(target_timestamp - exp_timestamp)
#             access_token = create_access_token(
#                 identity=get_jwt_identity())
#             set_access_cookies(response, access_token, domain=DOMAIN)
#         return response
#     except (RuntimeError, KeyError):
#         # Case where there is not a valid JWT. Just return the original response
#         return response


@bp.route("/login", methods=["POST"])
def login():
    body = request.json
    if body is None:
        return responses.json_res(make_response(), {"success": False}, 400)
    username = body.get("username")
    if username is None:
        return responses.json_res(
            make_response(),
            {"success": False, "message": "username is not in body"},
            400,
        )
    user = get_user(username)
    if user is None:
        response = jsonify({"success": False, "message": "User doesn't exist"})
        return response, 404
    if user.password != body.get("password"):
        return responses.json_res(
            make_response(), {"success": False, "message": "wrong password"}, 400
        )
    if user is None:
        return responses.json_res(
            make_response(), {"success": False, "message": "user not found"}, 404
        )
    response = jsonify({"success": True, "message": "Login success!"})
    access_token = create_access_token(identity=username)
    set_access_cookies(response, access_token, domain=DOMAIN)
    return response


@bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    response = jsonify({"success": True, "message": "Successfully logged out!"})
    unset_access_cookies(response, domain=DOMAIN)
    return response


@bp.route("/register", methods=["POST"])
def register():
    body = request.json

    validator = Validator(signup_schema)
    validate_payload = {
        "username": body.get("username"),
        "password": body.get("password"),
        "signup_code": body.get("signup_code"),
    }

    is_valid = validator.validate(validate_payload)
    if is_valid is False:
        response = make_response()
        response.status_code = 400
        response.data = json.dumps(
            {
                "success": False,
                "message": "validation error",
                "errors": validator.errors,
            }
        )
        response.content_type = "application/json"
        return response

    # check if signup_code match the master signup code
    if validate_payload["signup_code"] != MASTER_SIGNUP_CODE:
        return responses.json_res(
            make_response(), {"success": False, "message": "invalid signup code"}, 400
        )

    user = create_user(validate_payload["username"], validate_payload["password"])
    if user is False:
        response = make_response()
        response.status_code = 400
        response.data = json.dumps(
            {
                "success": False,
                "message": "User already exist",
            }
        )
        response.content_type = "application/json"
        return response

    response = make_response()
    response.status_code = 201
    response.data = json.dumps(
        {"success": True, "message": "User created", "id": user.pk}
    )
    response.content_type = "application/json"
    access_token = create_access_token(identity=validate_payload["username"])
    set_access_cookies(response, access_token, domain=DOMAIN)
    return response


@bp.route("/me", methods=["GET"])
@jwt_required()
def handle_me():
    response = jsonify({"identity": get_jwt_identity()})
    return response
