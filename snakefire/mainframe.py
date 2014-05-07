import copy
import datetime
import os
import platform
import sys
import tempfile
import time
import urllib2
import enchant

from snakefire import NOTIFICATIONS_ENABLED, KDE_ENABLED

from PyQt4 import Qt
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import QtWebKit

if KDE_ENABLED:
    from PyKDE4 import kdecore
    from PyKDE4 import kdeui
elif NOTIFICATIONS_ENABLED:
    import subprocess
    import pynotify

import keyring

from campfireworker import CampfireWorker
from dialogs import AboutDialog, AlertsDialog, OptionsDialog
from renderers import MessageRenderer
from qtx import ClickableQLabel, IdleTimer, SpellTextEditor, TabWidgetFocusEventFilter
from systray import Systray

class Snakefire(object):
    DOMAIN = "www.snakefire.org"
    NAME = "Snakefire"
    DESCRIPTION = "Snakefire: Campfire Linux Client"
    VERSION = "1.0.3"
    ICON = "snakefire.png"
    MAC_TRAY_ICON = "snakefire-gray.png"
    COLORS = {
        "normal": None,
        "new": QtGui.QColor(0, 0, 255),
        "alert": QtGui.QColor(255, 0, 0)
    }

    def __init__(self):
        self.DESCRIPTION = self._(self.DESCRIPTION)
        self._pingTimer = None
        self._idleTimer = None
        self._idle = False
        self._lastIdleAnswer = None
        self._worker = None
        self._settings = {}
        self._canConnect = False
        self._cfDisconnected()

        if len(sys.argv) > 1:
            self._qsettings = QtCore.QSettings(sys.argv[1], QtCore.QSettings.IniFormat if sys.platform.find("win") == 0 else QtCore.QSettings.NativeFormat)
        else:
            self._qsettings = QtCore.QSettings(self.NAME, self.NAME)

        self._icon = QtGui.QIcon(":/icons/{icon}".format(icon=self.ICON))
        if platform.system()=="Darwin":
            self._trayIconIcon = QtGui.QIcon(":/icons/{icon}".format(icon=self.MAC_TRAY_ICON))
        else:
            self._trayIconIcon = self._icon
        self.setWindowIcon(self._icon)
        self.setAcceptDrops(True)
        self._setupUI()

        settings = self.getSettings("connection")

        self._canConnect = False
        if settings["subdomain"] and settings["user"] and settings["password"]:
            self._canConnect = True

        self._updateLayout()

        if not self._canConnect:
            self.options()
        elif settings["connect"]:
            self.connectNow()

    def showEvent(self, event):
        if self._trayIcon.isVisible():
            if self._trayIcon.isAlerting():
                self._trayIcon.stopAlert()
            return
        self._trayIcon.show()

    def dragEnterEvent(self, event):
        room = self.getCurrentRoom()
        canUpload = not self._rooms[room.id]["upload"] if room else False
        if canUpload and self._getDropFile(event):
            event.acceptProposedAction()

    def dropEvent(self, event):
        room = self.getCurrentRoom()
        path = self._getDropFile(event)
        if room and path:
            self._upload(room, path)

    def _getDropFile(self, event):
        files = []
        urls = event.mimeData().urls()
        if urls:
            for url in urls:
                path = url.path()
                if path and os.path.exists(path) and os.path.isfile(path):
                    try:
                        handle = open(str(path))
                        handle.close()
                        files.append(str(path))
                    except:
                        pass
            if len(files) > 1:
               files = []
        return files[0] if files else None

    def getSetting(self, group, setting):
        settings = self.getSettings(group, asString=False);
        return settings[setting] if setting in settings else None

    def setSetting(self, group, setting, value):
        self._qsettings.beginGroup(group);
        self._qsettings.setValue(setting, value)
        self._qsettings.endGroup();

    def getSettings(self, group, asString=True, reload=False):
        try:
            spell_language = SpellTextEditor.defaultLanguage()
        except enchant.errors.Error:
            spell_language = None
        defaults = {
            "connection": {
                "subdomain": None,
                "user": None,
                "password": None,
                "ssl": False,
                "connect": False,
                "join": False,
                "rooms": []
            },
            "program": {
                "minimize": False,
                "spell_language": spell_language,
                "away": True,
                "away_time": 10,
                "away_time_between_messages": 5,
                "away_message": self._("I am currently away from {name}").format(name=self.NAME)
            },
            "display": {
                "theme": "default",
                "size": 100,
                "show_join_message": True,
                "show_part_message": True,
                "show_message_timestamps": True
            },
            "alerts": {
                "notify_ping": True,
                "notify_inactive_tab": False,
                "notify_blink": True,
                "notify_notify": True
            },
            "matches": []
        }

        if reload or not group in self._settings:
            settings = defaults[group] if group in defaults else {}

            if group == "matches":
                settings = []
                size = self._qsettings.beginReadArray("matches")
                for i in range(size):
                    self._qsettings.setArrayIndex(i)
                    isRegex = False
                    try:
                        isRegex = True if ["true", "1"].index(str(self._qsettings.value("regex").toPyObject()).lower()) >= 0 else False
                    except:
                        pass

                    settings.append({
                        'regex': isRegex,
                        'match': self._qsettings.value("match").toPyObject()
                    })
                self._qsettings.endArray()
            else:
                self._qsettings.beginGroup(group);
                for setting in self._qsettings.childKeys():
                    settings[str(setting)] = self._qsettings.value(setting).toPyObject()
                self._qsettings.endGroup();

                boolSettings = []
                if group == "connection":
                    boolSettings += ["ssl", "connect", "join"]
                elif group == "program":
                    boolSettings += ["away", "minimize"]
                elif group == "display":
                    boolSettings += ["show_join_message", "show_part_message", "show_message_timestamps"]
                elif group == "alerts":
                    boolSettings += ["notify_ping", "notify_inactive_tab", "notify_blink", "notify_notify"]

                for boolSetting in boolSettings:
                    try:
                        settings[boolSetting] = True if ["true", "1"].index(str(settings[boolSetting]).lower()) >= 0 else False
                    except:
                        settings[boolSetting] = False

                if group == "connection" and settings["subdomain"] and settings["user"]:
                    settings["password"] = keyring.get_password(self.NAME, str(settings["subdomain"])+"_"+str(settings["user"]))

            self._settings[group] = settings

        settings = self._settings[group]
        if asString:
            if isinstance(settings, list):
                for i, row in enumerate(settings):
                    for setting in row:
                        if not isinstance(row[setting], bool):
                            settings[i][setting] = str(row[setting]) if row[setting] else ""
            else:
                for setting in settings:
                    if not isinstance(settings[setting], bool):
                        settings[setting] = str(settings[setting]) if settings[setting] else ""

        return settings

    def setSettings(self, group, settings):
        self._settings[group] = settings;

        if group == "matches":
            self._qsettings.beginWriteArray("matches")
            for i, setting in enumerate(settings):
                self._qsettings.setArrayIndex(i)
                self._qsettings.setValue("regex", setting["regex"])
                self._qsettings.setValue("match", setting["match"])
            self._qsettings.endArray()
        else:
            self._qsettings.beginGroup(group);
            for setting in self._settings[group]:
                if group != "connection" or setting != "password":
                    self._qsettings.setValue(setting, settings[setting])
                elif settings["subdomain"] and settings["user"]:
                    keyring.set_password(self.NAME, settings["subdomain"]+"_"+settings["user"], settings[setting])
            self._qsettings.endGroup();

            if group == "connection":
                self._canConnect = False
                if settings["subdomain"] and settings["user"] and settings["password"]:
                    self._canConnect = True
                self._updateLayout()
            elif group == "program":
                if settings["away"] and self._connected:
                    self._setUpIdleTracker()
                else:
                    self._setUpIdleTracker(False)
                if self._editor:
                    if settings["spell_language"]:
                        self._editor.enableSpell(settings["spell_language"])
                    else:
                        self._editor.disableSpell()
            elif group == "display":
                for roomId in self._rooms.keys():
                    if roomId in self._rooms and self._rooms[roomId]["view"]:
                        self._rooms[roomId]["view"].updateTheme(settings["theme"], settings["size"])

    def exit(self):
        self._forceClose = True
        self.close()

    def changeEvent(self, event):
        if self.getSetting("program", "minimize") and event.type() == QtCore.QEvent.WindowStateChange and self.isMinimized():
            self.hide()
            event.ignore()
        else:
            event.accept()

    def closeEvent(self, event):
        if (not hasattr(self, "_forceClose") or not self._forceClose) and self.getSetting("program", "minimize"):
            self.hide()
            event.ignore()
        else:
            if self.getSetting("connection", "join"):
                self.setSetting("connection", "rooms", ",".join([str(roomId) for roomId in self._rooms.keys()]))

            self.disconnectNow()

            if hasattr(self, "_workers") and self._workers:
                for worker in self._workers:
                    worker.terminate()
                    worker.wait()

            if hasattr(self, "_worker") and self._worker:
                self._worker.terminate()
                self._worker.wait()

            self.setSetting("window", "size", self.size())
            self.setSetting("window", "position", self.pos())

            event.accept()

    def alerts(self):
        dialog = AlertsDialog(self)
        dialog.open()

    def options(self):
        dialog = OptionsDialog(self)
        dialog.open()

    def about(self):
        dialog = AboutDialog(self)
        dialog.open()

    def connectNow(self):
        if not self._canConnect:
            return

        self._connecting = True
        self.statusBar().showMessage(self._("Connecting with Campfire..."))
        self._updateLayout()

        settings = self.getSettings("connection")

        self._worker = CampfireWorker(settings["subdomain"], settings["user"], settings["password"], settings["ssl"], self)
        self._connectWorkerSignals(self._worker)
        self._worker.connect()

    def disconnectNow(self):
        self.statusBar().showMessage(self._("Disconnecting from Campfire..."))
        if self._worker and hasattr(self, "_rooms"):
            # Using keys() since the dict could be changed (by _cfRoomLeft())
            # while iterating on it
            for roomId in self._rooms.keys():
                if roomId in self._rooms and self._rooms[roomId]["room"]:
                    self._worker.leave(self._rooms[roomId]["room"], False)

        self._cfDisconnected()
        self._updateLayout()

    def joinRoom(self, roomIndex=None):
        room = self._roomInIndex(roomIndex if roomIndex else self._toolBar["rooms"].currentIndex())
        if not room:
            return

        self._toolBar["join"].setEnabled(False)
        self.statusBar().showMessage(unicode(self._("Joining room {room}...").format(room=room["name"])))

        self._rooms[room["id"]] = {
            "room": None,
            "stream": None,
            "upload": None,
            "tab": None,
            "view": None,
            "frame": None,
            "usersList": None,
            "topicLabel": None,
            "filesLabel": None,
            "uploadButton": None,
            "uploadLabel": None,
            "uploadWidget": None,
            "newMessages": 0,
            "currentScrollbarValue": 0,
            "currentScrollbarMax": 0
        }
        self._getWorker().join(room["id"])

    def ping(self):
        if not self._connected:
            return
        for roomId in self._rooms.keys():
            if roomId in self._rooms and self._rooms[roomId]["room"]:
                self.updateRoomUsers(roomId, pinging=True)

    def speak(self):
        message = self._editor.document().toPlainText()
        room = self.getCurrentRoom()
        if not room or message.trimmed().isEmpty():
            return

        self._editor.document().clear()

        if message[0] == '/':
            command = QtCore.QString(message)
            separatorIndex = command.indexOf(QtCore.QRegExp('\\s'));
            handled = self.command(command.mid(1, separatorIndex-1), command.mid(separatorIndex + 1 if separatorIndex >= 0 else command.length()))
            if handled:
                return

        self.statusBar().showMessage(unicode(self._("Sending message to {room}...").format(room=room.name)))
        self._getWorker().speak(room, unicode(message))

    def command(self, command, args):
        if command.compare(QtCore.QString("away"), QtCore.Qt.CaseInsensitive) == 0:
            self.toggleAway()
            return True

    def uploadFile(self):
        room = self.getCurrentRoom()
        if not room:
            return

        path = QtGui.QFileDialog.getOpenFileName(self, self._("Select file to upload"))
        if path:
            self._upload(room, str(path))

    def uploadCancel(self):
        room = self.getCurrentRoom()
        if not room:
            return

        if self._rooms[room.id]["upload"]:
            self._rooms[room.id]["upload"].stop().join()
            self._rooms[room.id]["upload"] = None

        self._rooms[room.id]["uploadWidget"].hide()

    def leaveRoom(self, roomId):
        if roomId in self._rooms:
            self.statusBar().showMessage(unicode(self._("Leaving room {room}...").format(room=self._rooms[roomId]["room"].name)))
            self._getWorker().leave(self._rooms[roomId]["room"])

    def changeTopic(self):
        room = self.getCurrentRoom()
        if not room:
            return
        topic, ok = QtGui.QInputDialog.getText(self,
            self._("Change topic"),
            unicode(self._("Enter new topic for room {room}").format(room=room.name)),
            QtGui.QLineEdit.Normal,
            room.topic
        )
        if ok:
            self.statusBar().showMessage(unicode(self._("Changing topic for room {room}...").format(room=room.name)))
            self._getWorker().changeTopic(room, topic)

    def updateRoomUsers(self, roomId = None, pinging = False):
        if not roomId:
            room = self.getCurrentRoom()
            if room:
                roomId = room.id
        if roomId in self._rooms:
            if not pinging:
                self.statusBar().showMessage(unicode(self._("Getting users in {room}...").format(room=self._rooms[roomId]["room"].name)))
            self._getWorker().users(self._rooms[roomId]["room"], pinging)

    def updateRoomUploads(self, roomId = None):
        if not roomId:
            room = self.getCurrentRoom()
            if room:
                roomId = room.id
        if roomId in self._rooms:
            self.statusBar().showMessage(unicode(self._("Getting uploads from {room}...").format(room=self._rooms[roomId]["room"].name)))
            self._getWorker().uploads(self._rooms[roomId]["room"])

    def getCurrentRoom(self):
        index = self._tabs.currentIndex()
        for roomId in self._rooms.keys():
            if roomId in self._rooms and self._rooms[roomId]["tab"] == index:
                return self._rooms[roomId]["room"]

    def toggleAway(self):
        self.setAway(False if self._idle else True)

    def setAway(self, away=True):
        self._idle = away
        self.statusBar().showMessage(self._("You are now away") if self._idle else self._('You are now active'), 5000)

    def onIdle(self):
        self.setAway(True)

    def onActive(self):
        self.setAway(False)

    def _setUpIdleTracker(self, enable=True):
        if self._idleTimer:
            self._idleTimer.stop()
            self._idleTimer = None

        if enable and IdleTimer.supported():
            self._idleTimer = IdleTimer(self, int(self.getSetting("program", "away_time")) * 60)
            self.connect(self._idleTimer, QtCore.SIGNAL("idle()"), self.onIdle)
            self.connect(self._idleTimer, QtCore.SIGNAL("active()"), self.onActive)
            self._idleTimer.start()

    def _cfStreamMessage(self, room, message, live=True, updateRoom=True):
        if (
            not message.user or
            (live and message.is_text() and message.is_by_current_user()) or
            not room.id in self._rooms
        ):
            return

        view = self._rooms[room.id]["view"]
        if not view:
            return

        alert = False
        alertIsDirectPing = False

        if message.is_text() and not message.is_by_current_user():
            alertIsDirectPing = (QtCore.QString(message.body).indexOf(QtCore.QRegExp("\\s*\\b{name}\\b".format(name=QtCore.QRegExp.escape(self._worker.getUser().name)), QtCore.Qt.CaseInsensitive)) == 0)
            alert = self.getSetting("alerts", "notify_ping") if alertIsDirectPing else self._matchesAlert(message.body)

        maximumImageWidth = int(view.size().width() * 0.4) # 40% of viewport
        renderer = MessageRenderer(
            self._worker.getApiToken(),
            maximumImageWidth,
            room,
            message,
            live=live,
            updateRoom=updateRoom,
            showTimestamps = self.getSetting("display", "show_message_timestamps"),
            alert=alert,
            alertIsDirectPing=alertIsDirectPing,
            parent=self
        )

        if renderer.needsThread():
            self.connect(renderer, QtCore.SIGNAL("render(PyQt_PyObject, PyQt_PyObject, PyQt_PyObject, PyQt_PyObject, PyQt_PyObject, PyQt_PyObject, PyQt_PyObject)"), self._renderMessage)
            renderer.start()
        else:
            self._renderMessage(renderer.render(), room, message, live=live, updateRoom=updateRoom, alert=alert, alertIsDirectPing=alertIsDirectPing)

    def _renderMessage(self, html, room, message, live=True, updateRoom=True, alert=False, alertIsDirectPing=False):
        if (not room.id in self._rooms):
            return

        frame = self._rooms[room.id]["frame"]
        view = self._rooms[room.id]["view"]
        if not frame or not view:
            return

        if not self.getSetting("display", "show_join_message") and (message.is_joining() or message.is_leaving() or message.is_kick()):
            return

        if html:
            self._rooms[room.id]["currentScrollbarValue"] = frame.scrollPosition().y()
            self._rooms[room.id]["currentScrollbarMax"] = frame.scrollBarMaximum(QtCore.Qt.Vertical)
            frame.setHtml(frame.toHtml() + html)
            view.show()

            tabIndex = self._rooms[room.id]["tab"]
            tabBar = self._tabs.tabBar()
            isActiveTab = (self.isActiveWindow() and tabIndex == self._tabs.currentIndex())

            if message.is_text() and not isActiveTab:
                self._rooms[room.id]["newMessages"] += 1

            if self._rooms[room.id]["newMessages"] > 0:
                tabBar.setTabText(tabIndex, unicode("{room} ({count})".format(room = room.name, count = self._rooms[room.id]["newMessages"])))

            if not isActiveTab and (alert or self._rooms[room.id]["newMessages"] > 0) and tabBar.tabTextColor(tabIndex) == self.COLORS["normal"]:
                tabBar.setTabTextColor(tabIndex, self.COLORS["alert" if alert else "new"])

            notifyInactiveTab = self.getSetting("alerts", "notify_inactive_tab")

            if (not isActiveTab and (alert or notifyInactiveTab)) and self.getSetting("alerts", "notify_blink"):
                self._trayIcon.alert()

            if live and ((alert or (not isActiveTab and notifyInactiveTab and message.is_text())) and self.getSetting("alerts", "notify_notify")):
                self._notify(room, unicode(u"{} says: {}".format(message.user.name, message.body)), message.user)

        if updateRoom:
            if (message.is_joining() or message.is_leaving()):
                self.updateRoomUsers(room.id)
            elif message.is_upload():
                self.updateRoomUploads(room.id)
            elif message.is_topic_change() and not message.is_by_current_user():
                self._cfTopicChanged(room, message.body)

        # Respond to direct pings while being away, but only send an auto-response if last one was sent more than 2 minutes ago
        if live and alertIsDirectPing and self.getSetting("program", "away") and self._idle:
            if self._lastIdleAnswer is None or time.time() - self._lastIdleAnswer >= (int(self.getSetting("program", "away_time_between_messages")) * 60):
                self._lastIdleAnswer = time.time()
                self._getWorker().speak(room, unicode("{user}: {message}".format(
                    user = message.user.name,
                    message = self.getSetting("program", "away_message")
                )))

    def _matchesAlert(self, message):
        matches = False
        searchMatches = self.getSettings("matches")
        for match in searchMatches:
            regex = "\\b{word}\\b".format(word=QtCore.QRegExp.escape(match['match'])) if not match['regex'] else match['match']
            if QtCore.QString(message).contains(QtCore.QRegExp(regex, QtCore.Qt.CaseInsensitive)):
                matches = True
                break
        return matches

    def _cfConnected(self, user, rooms):
        self._connecting = False
        self._connected = True
        self._rooms = {}

        self._toolBar["rooms"].clear()
        for room in rooms:
            self._toolBar["rooms"].addItem(room["name"], room)

        self.statusBar().showMessage(unicode(self._("{user} connected to Campfire").format(user=user.name)), 5000)
        self._updateLayout()

        if not self._pingTimer:
            self._pingTimer = QtCore.QTimer(self)
            self.connect(self._pingTimer, QtCore.SIGNAL("timeout()"), self.ping)
        self._pingTimer.start(60000) # Ping every minute

        if self.getSetting("program", "away"):
            self._setUpIdleTracker()

        if self.getSetting("connection", "join"):
            rooms = self.getSetting("connection", "rooms")
            if rooms:
                for roomId in rooms.split(","):
                    count = self._toolBar["rooms"].count()
                    if count:
                        roomIndex = None
                        for i in range(count):
                            data = self._toolBar["rooms"].itemData(i)
                            if not data.isNull():
                                data = data.toMap()
                                for key in data:
                                    if str(key) == "id" and str(data[key].toString()) == roomId:
                                        roomIndex = i
                                        break;
                                if roomIndex is not None:
                                    break
                        if roomIndex is not None:
                            self.joinRoom(roomIndex)

    def _cfDisconnected(self):
        if self._pingTimer:
            self._pingTimer.stop()
            self._pingTimer = None

        if self._idleTimer:
            self._setUpIdleTracker(False)

        self._connecting = False
        self._connected = False
        self._rooms = {}
        self._worker = None
        self.statusBar().clearMessage()

    def _cfRoomJoined(self, room, messages=[], rejoined=False):
        if room.id not in self._rooms:
            return

        if not rejoined:
            self._rooms[room.id].update(self._setupRoomUI(room))
            self._rooms[room.id]["room"] = room
        self._rooms[room.id]["stream"] = self._worker.getStream(room)
        self.updateRoomUsers(room.id)
        self.updateRoomUploads(room.id)
        if not rejoined:
            self.statusBar().showMessage(unicode(self._("Joined room {room}").format(room=room.name)), 5000)
        self._updatedRoomsList()
        if not rejoined and messages:
            for message in messages:
                self._cfStreamMessage(room, message, live=False, updateRoom=False)

    def _cfSpoke(self, room, message):
        self._cfStreamMessage(room, message, live=False)
        self.statusBar().clearMessage()

    def _cfRoomLeft(self, room):
        if self._rooms[room.id]["stream"]:
            self._rooms[room.id]["stream"].stop().join()
        if self._rooms[room.id]["upload"]:
            self._rooms[room.id]["upload"].stop().join()

        self._tabs.removeTab(self._rooms[room.id]["tab"])
        del self._rooms[room.id]
        self.statusBar().showMessage(unicode(self._("Left room {room}").format(room=room.name)), 5000)
        self._updatedRoomsList()

    def _cfRoomUsers(self, room, users, pinging=False):
        # We may be disconnecting while still processing the list
        if not room.id in self._rooms:
            return

        if not pinging:
            self.statusBar().clearMessage()

        user_list = self._rooms[room.id]["usersList"]
        # First check that we have created the user_list object.
        if user_list is None:
            return

        user_list.clear()
        for user in users:
            item = QtGui.QListWidgetItem(user["name"])
            item.setData(QtCore.Qt.UserRole, user)
            user_list.addItem(item)

    def _cfRoomUploads(self, room, uploads):
        # We may be disconnecting while still processing the list
        if not room.id in self._rooms:
            return

        self.statusBar().clearMessage()
        label = self._rooms[room.id]["filesLabel"]
        if uploads:
            html = ""
            for upload in uploads:
                html += "{br}&bull; <a href=\"{url}\">{name}</a>".format(
                    br = "<br />" if html else "",
                    url = upload["full_url"],
                    name = upload["name"]
                )
            html = unicode("{text}<br />{html}".format(
                text = self._("Latest uploads:"),
                html = html
            ))

            label.setText(html)
            if not label.isVisible():
                label.show()
        elif label.isVisible():
            label.setText("")
            label.hide()

    def _cfUploadProgress(self, room, current, total):
        if not room.id in self._rooms:
            return

        progressBar = self._rooms[room.id]["uploadProgressBar"]
        if not self._rooms[room.id]["uploadWidget"].isVisible():
            self._rooms[room.id]["uploadWidget"].show()
            progressBar.setMaximum(total)

        progressBar.setValue(current)

    def _cfUploadFinished(self, room):
        if not room.id in self._rooms:
            return

        self._rooms[room.id]["upload"].join()
        self._rooms[room.id]["upload"] = None
        self._rooms[room.id]["uploadWidget"].hide()

    def _cfTopicChanged(self, room, topic):
        if not room.id in self._rooms:
            return

        self._rooms[room.id]["topicLabel"].setText(topic)
        self.statusBar().clearMessage()

    def _cfConnectError(self, error):
        self._cfDisconnected()
        self._updateLayout()
        self._cfError(error)

    def _cfError(self, error):
        self.statusBar().clearMessage()
        if not self._connected:
            QtGui.QMessageBox.critical(self, "Error", self._("Error while connecting: {error}".format(error = str(error))))
        else:
            QtGui.QMessageBox.critical(self, "Error", str(error))

    def _cfRoomError(self, error, room):
        self.statusBar().clearMessage()
        if isinstance(error, RuntimeError):
            (code, message) = error
            if code == 401:
                self.statusBar().showMessage(unicode(self._("Disconnected from room. Rejoining room {room}...").format(room=room.name)), 5000)
                self._rooms[room.id]["stream"].stop().join()
                self._getWorker().join(room.id, True)
                return
        QtGui.QMessageBox.critical(self, "Error", str(error))

    def _roomSelected(self, index):
        self._updatedRoomsList(index)

    def _upload(self, room, path):
        self._rooms[room.id]["upload"] = self._worker.upload(room, path)
        self._updateRoomLayout()

    def _roomTabClose(self, tabIndex):
        for roomId in self._rooms:
            if self._rooms[roomId]["tab"] == tabIndex:
                self.leaveRoom(roomId)
                break

    def _roomTabFocused(self):
        tabIndex = self._tabs.currentIndex()
        if tabIndex < 0 or not self.isActiveWindow():
            return

        room = self._roomInTabIndex(tabIndex)
        if not room:
            return

        tabBar = self._tabs.tabBar()

        if self._rooms[room.id]["newMessages"] > 0:
            self._rooms[room.id]["newMessages"] = 0
            tabBar.setTabText(tabIndex, room.name)

        if tabBar.tabTextColor(tabIndex) != self.COLORS["normal"]:
            tabBar.setTabTextColor(tabIndex, self.COLORS["normal"])

        self._updateRoomLayout()

    def _roomInTabIndex(self, index):
        room = None
        for key in self._rooms:
            if self._rooms[key]["tab"] == index:
                room = self._rooms[key]["room"]
                break
        return room

    def _roomInIndex(self, index):
        room = {}
        data = self._toolBar["rooms"].itemData(index)
        if not data.isNull():
            data = data.toMap()
            for key in data:
                room[str(key)] = unicode(data[key].toString())
        return room

    def _connectWorkerSignals(self, worker):
        self.connect(worker, QtCore.SIGNAL("error(PyQt_PyObject)"), self._cfError)
        self.connect(worker, QtCore.SIGNAL("connected(PyQt_PyObject, PyQt_PyObject)"), self._cfConnected)
        self.connect(worker, QtCore.SIGNAL("connectError(PyQt_PyObject)"), self._cfConnectError)
        self.connect(worker, QtCore.SIGNAL("streamError(PyQt_PyObject, PyQt_PyObject)"), self._cfRoomError)
        self.connect(worker, QtCore.SIGNAL("uploadError(PyQt_PyObject, PyQt_PyObject)"), self._cfRoomError)
        self.connect(worker, QtCore.SIGNAL("joined(PyQt_PyObject, PyQt_PyObject, PyQt_PyObject)"), self._cfRoomJoined)
        self.connect(worker, QtCore.SIGNAL("spoke(PyQt_PyObject, PyQt_PyObject)"), self._cfSpoke)
        self.connect(worker, QtCore.SIGNAL("streamMessage(PyQt_PyObject, PyQt_PyObject, PyQt_PyObject)"), self._cfStreamMessage)
        self.connect(worker, QtCore.SIGNAL("left(PyQt_PyObject)"), self._cfRoomLeft)
        self.connect(worker, QtCore.SIGNAL("users(PyQt_PyObject, PyQt_PyObject, PyQt_PyObject)"), self._cfRoomUsers)
        self.connect(worker, QtCore.SIGNAL("uploads(PyQt_PyObject, PyQt_PyObject)"), self._cfRoomUploads)
        self.connect(worker, QtCore.SIGNAL("uploadProgress(PyQt_PyObject, PyQt_PyObject, PyQt_PyObject)"), self._cfUploadProgress)
        self.connect(worker, QtCore.SIGNAL("uploadFinished(PyQt_PyObject)"), self._cfUploadFinished)
        self.connect(worker, QtCore.SIGNAL("topicChanged(PyQt_PyObject, PyQt_PyObject)"), self._cfTopicChanged)

    def _getWorker(self):
        if not hasattr(self, "_workers"):
            self._workers = []

        if self._workers:
            for worker in self._workers:
                if worker.isFinished():
                    return worker

        worker = copy.copy(self._worker)
        self._connectWorkerSignals(worker)
        self._workers.append(worker)
        return worker

    def _updatedRoomsList(self, index=None):
        if not index:
            index = self._toolBar["rooms"].currentIndex()

        room = self._roomInIndex(index)

        self._toolBar["join"].setEnabled(False)
        if not room or room["id"] not in self._rooms:
            self._toolBar["join"].setEnabled(True)

        centralWidget = self.centralWidget()
        if not self._tabs.count():
            centralWidget.hide()
        else:
            centralWidget.show()

    def _notify(self, room, message, user):
        raise NotImplementedError("_notify() must be implemented")

    def _updateRoomLayout(self):
        room = self.getCurrentRoom()
        if room:
            canUpload = not self._rooms[room.id]["upload"]
            uploadButton = self._rooms[room.id]["uploadButton"]
            if (
                (canUpload and not uploadButton.isEnabled()) or
                (not canUpload and uploadButton.isEnabled())
            ):
                uploadButton.setEnabled(canUpload)

    def _updateLayout(self):
        self._menus["file"]["connect"].setEnabled(not self._connected and self._canConnect and not self._connecting)
        self._menus["file"]["disconnect"].setEnabled(self._connected)

        roomsEmpty = self._toolBar["rooms"].count() == 1 and self._toolBar["rooms"].itemData(0).isNull()
        if not roomsEmpty and (not self._connected or not self._toolBar["rooms"].count()):
            self._toolBar["rooms"].clear()
            self._toolBar["rooms"].addItem(self._("No rooms available"))
            self._toolBar["rooms"].setEnabled(False)
        elif not roomsEmpty:
            self._toolBar["rooms"].setEnabled(True)

        self._toolBar["roomsLabel"].setEnabled(self._toolBar["rooms"].isEnabled())
        self._toolBar["join"].setEnabled(self._toolBar["rooms"].isEnabled())

    def _setupRoomUI(self, room):
        topic = room.topic if room.topic else ""
        topicLabel = ClickableQLabel(topic)
        topicLabel.setToolTip(self._("Click here to change room's topic"))
        topicLabel.setWordWrap(True)
        self.connect(topicLabel, QtCore.SIGNAL("clicked()"), self.changeTopic)

        view = SnakeFireWebView(self)
        view.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        frame = view.page().mainFrame()

        #Send all link clicks to systems web browser
        view.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)

        #Hide reload page context menu
        view.page().action(QtWebKit.QWebPage.Reload).setVisible(False)

        def linkClicked(url):
            QtGui.QDesktopServices.openUrl(url)
        view.connect(view, QtCore.SIGNAL("linkClicked (const QUrl&)"), linkClicked)

        # Support auto scroll when needed
        def autoScroll(size):
            active_room = self._rooms[room.id]

            # Use the frame set within the parent method if the frame key hasn't been populated
            active_room_frame = active_room["frame"] if active_room["frame"] else frame
            if active_room["currentScrollbarValue"] == active_room["currentScrollbarMax"]:
                active_room_frame.scroll(0, size.height())
            else:
                active_room_frame.scroll(0, active_room["currentScrollbarValue"])

        frame.connect(frame, QtCore.SIGNAL("contentsSizeChanged (const QSize&)"), autoScroll)

        usersList = QtGui.QListWidget()

        filesLabel = QtGui.QLabel("")
        filesLabel.setOpenExternalLinks(True)
        filesLabel.setWordWrap(True)
        filesLabel.hide()

        uploadButton = QtGui.QPushButton(self._("&Upload new file"))
        self.connect(uploadButton, QtCore.SIGNAL("clicked()"), self.uploadFile)

        uploadProgressBar = QtGui.QProgressBar()
        uploadProgressLabel = QtGui.QLabel(self._("Uploading:"))

        uploadCancelButton = QtGui.QPushButton(self._("Cancel"))
        self.connect(uploadCancelButton, QtCore.SIGNAL("clicked()"), self.uploadCancel)

        uploadLayout = QtGui.QHBoxLayout()
        uploadLayout.addWidget(uploadProgressLabel)
        uploadLayout.addWidget(uploadProgressBar)
        uploadLayout.addWidget(uploadCancelButton)

        uploadWidget = QtGui.QWidget()
        uploadWidget.setLayout(uploadLayout)
        uploadWidget.hide()

        leftFrameLayout = QtGui.QVBoxLayout()
        leftFrameLayout.addWidget(topicLabel)
        leftFrameLayout.addWidget(view)
        leftFrameLayout.addWidget(uploadWidget)

        rightFrameLayout = QtGui.QVBoxLayout()
        rightFrameLayout.addWidget(usersList)
        rightFrameLayout.addWidget(filesLabel)
        rightFrameLayout.addWidget(uploadButton)
        rightFrameLayout.addStretch(1)

        leftFrame = QtGui.QWidget()
        leftFrame.setLayout(leftFrameLayout)

        rightFrame = QtGui.QWidget()
        rightFrame.setLayout(rightFrameLayout)

        splitter = QtGui.QSplitter()
        splitter.addWidget(leftFrame)
        splitter.addWidget(rightFrame)
        splitter.setSizes([splitter.size().width() * 0.75, splitter.size().width() * 0.25])

        index = self._tabs.addTab(splitter, room.name)
        self._tabs.setCurrentIndex(index)

        if not self.COLORS["normal"]:
            self.COLORS["normal"] = self._tabs.tabBar().tabTextColor(index)
        else:
            self._tabs.tabBar().setTabTextColor(index, self.COLORS["normal"])

        return {
            "tab": index,
            "view": view,
            "frame": frame,
            "usersList": usersList,
            "topicLabel": topicLabel,
            "filesLabel": filesLabel,
            "uploadButton": uploadButton,
            "uploadWidget": uploadWidget,
            "uploadProgressBar": uploadProgressBar,
            "uploadProgressLabel": uploadProgressLabel
        }

    def _setupUI(self):
        self.setWindowTitle(self.NAME)

        self._addMenu()
        self._addToolbar()

        self._tabs = QtGui.QTabWidget()
        self._tabs.setTabsClosable(True)
        self.connect(self._tabs, QtCore.SIGNAL("currentChanged(int)"), self._roomTabFocused)
        self.connect(self._tabs, QtCore.SIGNAL("tabCloseRequested(int)"), self._roomTabClose)

        self._editor = SpellTextEditor(lang=self.getSetting("program", "spell_language"), mainFrame=self)

        speakButton = QtGui.QPushButton(self._("&Send"))
        self.connect(speakButton, QtCore.SIGNAL('clicked()'), self.speak)

        grid = QtGui.QGridLayout()
        grid.setRowStretch(0, 1)
        grid.addWidget(self._tabs, 0, 0, 1, -1)
        grid.addWidget(self._editor, 2, 0)
        grid.addWidget(speakButton, 2, 1)

        widget = QtGui.QWidget()
        widget.setLayout(grid)
        self.setCentralWidget(widget)

        tabWidgetFocusEventFilter = TabWidgetFocusEventFilter(self)
        self.connect(tabWidgetFocusEventFilter, QtCore.SIGNAL("tabFocused()"), self._roomTabFocused)
        widget.installEventFilter(tabWidgetFocusEventFilter)

        self.centralWidget().hide()

        size = self.getSetting("window", "size")

        if not size:
            size = QtCore.QSize(640, 480)

        self.resize(size)

        position = self.getSetting("window", "position")
        if not position:
            screen = QtGui.QDesktopWidget().screenGeometry()
            position = QtCore.QPoint((screen.width()-size.width())/2, (screen.height()-size.height())/2)

        self.move(position)

        self._updateLayout()

        menu = QtGui.QMenu(self)
        menu.addAction(self._menus["file"]["connect"])
        menu.addAction(self._menus["file"]["disconnect"])
        menu.addSeparator()
        menu.addAction(self._menus["file"]["exit"])

        self._trayIcon = Systray(self._trayIconIcon, self)
        self._trayIcon.setContextMenu(menu)
        self._trayIcon.setToolTip(self.DESCRIPTION)

    def _addMenu(self):
        self._menus = {
            "file": {
                "connect": self._createAction(self._("&Connect"), self.connectNow, icon="connect.png"),
                "disconnect": self._createAction(self._("&Disconnect"), self.disconnectNow, icon="disconnect.png"),
                "exit": self._createAction(self._("E&xit"), self.exit)
            },
            "settings": {
                "alerts": self._createAction(self._("&Alerts..."), self.alerts, icon="alerts.png"),
                "options": self._createAction(self._("&Options..."), self.options)
            },
            "help": {
                "about": self._createAction(self._("A&bout"), self.about)
            }
        }

        menu = self.menuBar()

        file_menu = menu.addMenu(self._("&File"))
        file_menu.addAction(self._menus["file"]["connect"])
        file_menu.addAction(self._menus["file"]["disconnect"])
        file_menu.addSeparator()
        file_menu.addAction(self._menus["file"]["exit"])

        settings_menu = menu.addMenu(self._("S&ettings"))
        settings_menu.addAction(self._menus["settings"]["alerts"])
        settings_menu.addSeparator()
        settings_menu.addAction(self._menus["settings"]["options"])

        help_menu = menu.addMenu(self._("&Help"))
        help_menu.addAction(self._menus["help"]["about"])

    def _addToolbar(self):
        self._toolBar = {
            "connect": self._menus["file"]["connect"],
            "disconnect": self._menus["file"]["disconnect"],
            "roomsLabel": QtGui.QLabel(self._("Rooms:")),
            "rooms": QtGui.QComboBox(),
            "join": self._createAction(self._("Join room"), self.joinRoom, icon="join.png"),
            "alerts": self._menus["settings"]["alerts"]
        }

        self.connect(self._toolBar["rooms"], QtCore.SIGNAL("currentIndexChanged(int)"), self._roomSelected)

        toolBar = self.toolBar()
        toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        toolBar.addAction(self._toolBar["connect"])
        toolBar.addAction(self._toolBar["disconnect"])
        toolBar.addSeparator();
        toolBar.addWidget(self._toolBar["roomsLabel"])
        toolBar.addWidget(self._toolBar["rooms"])
        toolBar.addAction(self._toolBar["join"])
        toolBar.addSeparator();
        toolBar.addAction(self._toolBar["alerts"])

    def _createAction(self, text, slot=None, shortcut=None, icon=None,
        tip=None, checkable=False, signal="triggered()"):
        """ Create an action """
        action = QtGui.QAction(text, self)
        if icon is not None:
            if not isinstance(icon, QtGui.QIcon):
                action.setIcon(QtGui.QIcon(":/icons/{icon}".format(icon=icon)))
            else:
                action.setIcon(icon)
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            self.connect(action, QtCore.SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action

    def _(self, string, module=None):
        return str(QtCore.QCoreApplication.translate(module or Snakefire.NAME, string))

class QSnakefire(QtGui.QMainWindow, Snakefire):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        Snakefire.__init__(self)

    def toolBar(self):
        toolbar = self.addToolBar(self.NAME)
        return toolbar

    def _notify(self, room, message, user):
        self._trayIcon.showMessage(room.name, message)

if KDE_ENABLED:
    class KSnakefire(kdeui.KMainWindow, Snakefire):
        def __init__(self, parent=None):
            kdeui.KMainWindow.__init__(self, parent)
            Snakefire.__init__(self)

        def _notify(self, room, message, user):
            notification = kdeui.KNotification.event(
                "FilterAlert",
                message,
                QtGui.QPixmap(),
                self,
                kdeui.KNotification.CloseWhenWidgetActivated
            )

if NOTIFICATIONS_ENABLED:
    class GSnakefire(QSnakefire):
        def __init__(self, parent=None):
            super(GSnakefire, self).__init__(parent)
            pynotify.init("Snakefire")

        def _notify(self, room, message, user):
            title = unicode("Snakefire Room: {}".format(room.name))
            try:
                request = urllib2.Request(user.avatar_url)
                image = urllib2.urlopen(request).read()

                imageFile = tempfile.NamedTemporaryFile('w+b')
                imageFile.write(image)
                imageFile.flush()

                notify = pynotify.Notification(title, message, imageFile.name)
                notify.show()

                imageFile.close()
            except:
                subprocess.call(['notify-send', title, message])

def debug_trace():
  '''set a tracepoint in the python debugger that works with qt'''
  from PyQt4.QtCore import pyqtRemoveInputHook
  from pdb import set_trace
  pyqtRemoveInputHook()
  set_trace()

class SnakeFireWebView(QtWebKit.QWebView):
    def __init__(self, snakefire, parent=None):
        QtWebKit.QWebView.__init__(self, parent)
        self.snakefire = snakefire
        self.updateTheme()

    def updateTheme(self, theme = None, size=None):
        self.settings().setUserStyleSheetUrl(QtCore.QUrl("qrc:/themes/{theme}.css".format(
            theme = theme if theme else self.snakefire.getSetting("display", "theme")
        )))
        self.setTextSizeMultiplier(round(float(size if size else self.snakefire.getSetting("display", "size")) / 100, 1))

    def dragEnterEvent(self, event):
        return self.snakefire.dragEnterEvent(event)

    def dropEvent(self, event):
        return self.snakefire.dropEvent(event)
