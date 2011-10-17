import copy
import pyfire

from PyQt4 import QtCore

class CampfireWorker(QtCore.QThread):
    def __init__(self, subdomain, user, password, ssl=False, parent=None, campfire=None):
        super(CampfireWorker, self).__init__(parent)
        self._subdomain = subdomain
        self._user = user
        self._password = password
        self._ssl = ssl
        self._parent = parent
        self._action = None
        self._actionArgs = []
        self._campfire = campfire

    def __copy__(self):
        return CampfireWorker(
            self._subdomain,
            self._user,
            self._password,
            self._ssl,
            self._parent,
            copy.copy(self._campfire)
        )

    def connect(self):
        self._action = "_connect"
        self.start()

    def join(self, roomId, rejoin=False):
        self._action = "_join"
        self._actionArgs = [roomId, rejoin]
        self.start()

    def speak(self, room, message):
        self._action = "_speak"
        self._actionArgs = [room, message]
        self.start()

    def getStream(self, room):
        stream = room.get_stream(error_callback=self._streamError)
        stream.attach(lambda message: self._streamMessage(room, message))
        stream.start()
        return stream

    def getUser(self):
        return self._campfire.get_user() if self._campfire else None

    def getApiToken(self):
        return self._campfire.get_user().token if self._campfire else None

    def leave(self, room, useThread=True):
        self._action = "_leave"
        self._actionArgs = [room]
        if useThread:
            self.start()
        else:
            self._leave(room)

    def users(self, room, pinging=False):
        self._action = "_users"
        self._actionArgs = [room, pinging]
        self.start()

    def upload(self, room, path):
        upload = room.upload(
            path,
            progress_callback = lambda current, total: self._uploadProgress(room, current, total),
            finished_callback = lambda: self._uploadFinished(room),
            error_callback = self._uploadError
        )
        upload.start()
        return upload

    def uploads(self, room):
        self._action = "_uploads"
        self._actionArgs = [room]
        self.start()

    def changeTopic(self, room, topic):
        self._action = "_changeTopic"
        self._actionArgs = [room, str(topic)]
        self.start()

    def run(self):
        if self._action and hasattr(self, self._action):
            if not self._campfire:
                try:
                    self._campfire = pyfire.Campfire(self._subdomain, self._user, self._password, ssl=self._ssl)
                except Exception as e:
                    self.emit(QtCore.SIGNAL("connectError(PyQt_PyObject)"), e)

            try:
                getattr(self, self._action)(*self._actionArgs)
            except Exception as e:
                self.emit(QtCore.SIGNAL("error(PyQt_PyObject)"), e)
            finally:
                self._action = None
                self._actionArgs = []

    def _connect(self):
        if self._campfire:
            self.emit(QtCore.SIGNAL("connected(PyQt_PyObject, PyQt_PyObject)"), 
                self._campfire.get_user(),
                self._campfire.get_rooms()
            )

    def _join(self, roomId, rejoin):
        try:
            room = self._campfire.get_room(roomId)
        except Exception as e:
            self.emit(QtCore.SIGNAL("connectError(PyQt_PyObject)"), e)
            return

        room.join()
        room.id = str(room.id)
        recentMessages = room.recent() if not rejoin else None
        self.emit(QtCore.SIGNAL("joined(PyQt_PyObject, PyQt_PyObject, PyQt_PyObject)"), room, recentMessages, rejoin)

    def _speak(self, room, message):
        message = room.speak(message)
        self.emit(QtCore.SIGNAL("spoke(PyQt_PyObject, PyQt_PyObject)"), room, message)

    def _leave(self, room):
        room.leave()
        self.emit(QtCore.SIGNAL("left(PyQt_PyObject)"), room)

    def _streamError(self, e, room):
        self.emit(QtCore.SIGNAL("streamError(PyQt_PyObject, PyQt_PyObject)"), e, room)

    def _streamMessage(self, room, message, live=True):
        self.emit(QtCore.SIGNAL("streamMessage(PyQt_PyObject, PyQt_PyObject, PyQt_PyObject)"), 
            room,
            message,
            live
        )

    def _users(self, room, pinging=False):
        try:
            self.emit(QtCore.SIGNAL("users(PyQt_PyObject, PyQt_PyObject, PyQt_PyObject)"),
                room,
                room.get_users(),
                pinging
            )
        except Exception as e:
            if pinging:
                return
            raise e

    def _uploadError(self, e, room):
        self.emit(QtCore.SIGNAL("uploadError(PyQt_PyObject, PyQt_PyObject)"), e, room)

    def _uploadProgress(self, room, current, total):
        self.emit(QtCore.SIGNAL("uploadProgress(PyQt_PyObject, PyQt_PyObject, PyQt_PyObject)"), 
            room,
            current,
            total
        )

    def _uploadFinished(self, room):
        self.emit(QtCore.SIGNAL("uploadFinished(PyQt_PyObject)"), room)

    def _uploads(self, room):
        self.emit(QtCore.SIGNAL("uploads(PyQt_PyObject, PyQt_PyObject)"),
            room,
            room.get_uploads()
        )

    def _changeTopic(self, room, topic):
        room.set_topic(topic)
        self.emit(QtCore.SIGNAL("topicChanged(PyQt_PyObject, PyQt_PyObject)"),
            room,
            topic
        )

