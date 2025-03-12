import random
import json
import copy

from plexapi.server import PlayQueue, PlexServer
from melon import constants
from melon.config import Config
from melon.store import store
from melon.util import forwardRequest, requestToServer


PLUGIN_NAME = "ExploreRadio"
HIJACK = "hijack"
STATION_KEY = "explore"
DEFAULT_CONFIG = {"station_name": "Explore Radio"}


class Plugin:
    _server = None
    queues = {}
    inflight = False
    favorites = 1

    def __init__(self):
        _config = Config.getPluginSettins(PLUGIN_NAME)
        self.config = _config if _config else DEFAULT_CONFIG

    def setQueueIdForDevice(self, device, queueId):
        self.queues[device] = queueId

    def getQueueIdForRequest(self, request):
        deviceId = (
            request.args[constants.DEVICE_NAME_KEY]
            if constants.DEVICE_NAME_KEY in request.args
            else None
        )
        if deviceId and deviceId in self.queues:
            return self.queues[deviceId]
        return ""

    def server(self):
        if self._server is None:
            self._server = PlexServer(
                f"{Config.serverAddress}:{Config.serverPort}", store.token
            )
        return self._server

    def paths(self, request):
        queueId = self.getQueueIdForRequest(request)
        return {
            "hubs/sections/1": self.addExploreStation,
            "playQueues": self.startStation,
            f"playQueues/{str(queueId)}": self.playQueues,
        }

    def addExploreStation(self, _, __, response):
        print("Adding station...")
        return self.addStation(self.config["station_name"], STATION_KEY, response)

    def playQueues(self, path, request, response):
        queueId = str(self.getQueueIdForRequest(request))
        if queueId in path and not self.inflight:
            print("checking if we should add to queue")
            self.inflight = True
            self.handleQueue(request)
            self.inflight = False
            # refresh the response since we changed the queue
            return forwardRequest(request, path)

        return response

    def startStation(self, path, request, response):
        if (
            constants.URI_KEY in request.args
            and STATION_KEY in request.args[constants.URI_KEY]
            and HIJACK in request.args[constants.URI_KEY]
        ):
            print("Starting station...")
            section = self.server().library.section(Config.musicSection)

            # TODO: pick this in a smarter way
            firstTrack = section.searchTracks(maxresults=1, sort="random")[0]
            tracks = [firstTrack]
            server = self.server()
            queue = PlayQueue.create(server, tracks)

            prevTrack = firstTrack
            while len(queue.items) < 3:
                prevTrack = self.getNextTrack(server, prevTrack, queue.items)
                queue.addItem(prevTrack)

            deviceId = request.args[constants.DEVICE_NAME_KEY]
            self.setQueueIdForDevice(deviceId, queue.playQueueID)
            return requestToServer(
                f"playQueues/{str(queue.playQueueID)}", request.headers
            )
        return response

    def handleQueue(self, request):
        server = self.server()
        queueId = self.getQueueIdForRequest(request)
        queue = PlayQueue.get(server, queueId)
        queue.refresh()
        pos = len(queue.items) - queue.playQueueSelectedItemOffset
        print("pos", pos)
        while pos < 15:
            print("pos", pos)
            track = queue.items[-1]
            nextTrack = self.getNextTrack(server, track, queue.items)
            queue.addItem(nextTrack)
            pos = len(queue.items) - queue.playQueueSelectedItemOffset

    # TODO: from here down is a real mess
    def addStation(self, name, key, response):
        j = json.loads(response.content)
        for hub in j["MediaContainer"]["Hub"]:
            if hub["title"] == "Stations":
                hub["size"] = 5
                first = copy.deepcopy(hub["Metadata"][0])
                first["title"] = name
                first["guid"] = "hijack://station/" + key
                first["key"] = "/hijack/stations/" + key

                hub["Metadata"].insert(0, first)

        response._content = json.dumps(j)
        return response

    def getNextTrack(self, server, track, queue):
        tracks = track.sonicallySimilar(maxDistance=0.2)
        # make an unheard song more likely the more favorites in a row
        rand = random.randint(0, self.favorites)
        print(rand, self.favorites)
        unheard = rand < self.favorites
        if not unheard:
            self.favorites = self.favorites + 1
        else:
            self.favorites = 1
        type = "unheard" if unheard else "favorited"
        # TODO: super dumb
        filtered = list(
            filter(
                lambda t: t not in queue
                and (
                    t.viewCount < 1
                    if unheard
                    else t.userRating is not None and t.userRating > 0
                )
                and queue[-1].parentTitle
                != t.parentTitle,  # don't add two tracks from the same album back to back
                tracks,
            )
        )

        if len(filtered) < 1:
            unheard = not unheard
            type = "fell thru to unheard" if unheard else "fell thru to favorited"
            filtered = list(
                filter(
                    lambda t: t not in queue
                    and (
                        t.viewCount < 1
                        if unheard
                        else t.userRating is not None and t.userRating > 0
                    )
                    and queue[-1].parentTitle
                    != t.parentTitle,  # don't add two tracks from the same album back to back
                    tracks,
                )
            )

        if len(filtered) < 1:
            type = "fell through to rando"
            section = server.library.section(Config.musicSection)
            filtered = [section.searchTracks(maxresults=1, sort="random")[0]]

        print(type + ": ", filtered[0])
        return filtered[0]
