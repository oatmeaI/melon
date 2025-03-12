import random

from melon.config import Config
from melon import constants
from melon.store import store
from plexapi.server import PlexServer, PlayQueue
from melon.util import bail, forwardRequest, requestToServer

DEFAULT_CONFIG = {}
PLUGIN_NAME = "BetterTrackRadio"


class Plugin:
    _server = None
    queues = {}
    inflight = False
    favorites = 1

    def __init__(self):
        _config = Config.getPluginSettins(PLUGIN_NAME)
        self.config = _config if _config else DEFAULT_CONFIG

    def server(self):
        if self._server is None:
            self._server = PlexServer(
                f"{Config.serverAddress}:{Config.serverPort}", store.token
            )
        return self._server

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

    def paths(self, request):
        queueId = self.getQueueIdForRequest(request)
        return {
            "playQueues": self.startStation,
            f"playQueues/{str(queueId)}": self.handleQueue,
        }

    def startStation(self, path, request, response):
        # TODO: instead of try/except, detect the case correctly
        try:
            if constants.URI_KEY in request.args:
                uri = request.args[constants.URI_KEY]
                a = uri.find("library/metadata/") + 17
                b = uri.find("/station/")
                if a < 0 or b < 0:
                    return response
                ekey = int(uri[a:b])
                firstTrack = self.server().library.fetchItem(ekey)
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
        except Exception as e:
            print(e)
            return response
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

    def handleQueue(self, path, request, response):
        queueId = str(self.getQueueIdForRequest(request))
        if queueId in path and not self.inflight:
            print("checking if we should add to queue")
            self.inflight = True
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
            self.inflight = False
            # refresh the response since we changed the queue
            return forwardRequest(request, path)
        return response
