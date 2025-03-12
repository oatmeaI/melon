import requests
from flask import abort
from melon.config import Config


def buildResponse(response):
    return (
        response.content,
        response.status_code,
        [("Content-Type", response.headers["Content-Type"])],
    )


# Just a wrapper with a better name
def bail():
    abort(404)


def requestToServer(endpoint, headers):
    remote_url = f"{Config.serverAddress}:{Config.serverPort}/{endpoint}"
    esreq = requests.Request(
        method="get",
        url=remote_url,
        headers=headers,
    )
    with requests.Session() as s:
        resp = s.send(esreq.prepare(), stream=True)
        return resp


def forwardRequest(request, path):
    query_string = request.query_string.decode()
    remote_url = f"{Config.serverAddress}:{Config.serverPort}/{path}?{query_string}"
    req = requests.Request(
        method=request.method,
        url=remote_url,
        headers=request.headers,
        data=request.data,
    )
    with requests.Session() as s:
        resp = s.send(req.prepare(), stream=True)
        return resp
