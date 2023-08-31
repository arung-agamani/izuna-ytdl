from flask import Response
import json


def json_res(res: Response, data: any, status=200):
    res.data = json.dumps(data)
    # from pprint import pprint
    # pprint(res.data)
    res.content_type = "application/json"
    res.status_code = status
    return res
