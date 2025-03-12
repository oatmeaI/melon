from waitress import serve
from flask import Flask, request
import logging
import importlib

from melon.constants import PLUGIN_NAMESPACE, TOKEN_KEY
from melon.logging import logRequest
from melon.store import store
from melon.config import Config
from melon.util import bail, buildResponse, forwardRequest


app = Flask(__name__)
plugins = []

print("Enabled plugins: ", Config.enabled_plugins)
for plugin_name in Config.enabled_plugins:
    pluginModule = importlib.import_module(f"{PLUGIN_NAMESPACE}.{plugin_name}")
    plugin = pluginModule.Plugin()
    plugins.append(plugin)


@app.route("/<path:path>", methods=["POST", "GET", "PUT", "PATCH", "DELETE"])
def catch_all(path):
    if store.token is None and TOKEN_KEY in request.args:
        store.token = request.args[TOKEN_KEY]

    logRequest(path, request)

    handlers = []

    for plugin in plugins:
        if path in plugin.paths(request):
            handlers.append(plugin.paths(request)[path])
            break

    if len(handlers) == 0:
        bail()
        return

    response = forwardRequest(request, path)
    interceptedResponse = response

    for handler in handlers:
        interceptedResponse = handler(path, request, response)

    return buildResponse(interceptedResponse)


def start():
    if Config.debug:
        start_dev()
    else:
        serve(app, listen=f"*:{Config.port}")


def start_dev():
    Config.debug = True
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)
    app.run(port=Config.port, debug=True)
