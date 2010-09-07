import copy
import datetime
import os
import re
import sys

KDE_ENABLED = os.getenv("KDE_FULL_SESSION")

from PyQt4 import Qt
from PyQt4 import QtGui
from PyQt4 import QtCore

if KDE_ENABLED:
	from PyKDE4 import kdecore
	from PyKDE4 import kdeui

import keyring

from campfireworker import CampfireWorker
from dialogs import AlertsDialog, OptionsDialog
from qtx import Suggester, ClickableQLabel, SuggesterKeyPressEventFilter, TabWidgetFocusEventFilter
from systray import Systray

import resources

class Snakefire(object):
	DOMAIN = "snakefire.org"
	NAME = "Snakefire"
	DESCRIPTION = "Snakefire: Campfire Linux Client"
	VERSION = "1.0.1"
	ICON = "snakefire.png"
	COLORS = {
		"time": "c0c0c0",
		"alert": "ff0000",
		"join": "cb81cb",
		"leave": "cb81cb",
		"topic": "808080",
		"upload": "000000",
		"message": "000000",
		"nick": "808080",
		"nickAlert": "ff0000",
		"nickSelf": "000080",
		"tabs": {
			"normal": None,
			"new": QtGui.QColor(0, 0, 255),
			"alert": QtGui.QColor(255, 0, 0)
		}
	}

	def __init__(self):
		self.DESCRIPTION = self._(self.DESCRIPTION)
		self._worker = None
		self._settings = {}
		self._canConnect = False
		self._cfDisconnected()
		self._qsettings = QtCore.QSettings()
		self._icon = QtGui.QIcon(":/icons/%s" % (self.ICON))
		self.setWindowIcon(self._icon)
		self.setAcceptDrops(True)
		self._setupUI()

		settings = self.getSettings("connection")

		self._canConnect = False
		if settings["subdomain"] and settings["user"] and settings["password"]:
			self._canConnect = True

		self._updateLayout()

		if settings["connect"]:
			self.connectNow()

	def _(self, string, module=None):
		return str(QtCore.QCoreApplication.translate(module or Snakefire.NAME, string))

	def showEvent(self, event):
		if self._trayIcon.isVisible():
			if self._trayIcon.isAlerting():
				self._trayIcon.stopAlert()
			return
		self._trayIcon.show()

	def dragEnterEvent(self, event):
		room = self.getCurrentRoom()
		if room and self._getDropFiles(event):
			event.acceptProposedAction()

	def dropEvent(self, event):
		files = self._getDropFiles(event)

	def _getDropFiles(self, event):
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
					except Exception as e:
						pass
		return files

	def getSetting(self, group, setting):
		settings = self.getSettings(group, asString=False);
		return settings[setting] if setting in settings else None

	def setSetting(self, group, setting, value):
		self._qsettings.beginGroup(group);
		self._qsettings.setValue(setting, value)
		self._qsettings.endGroup();

	def getSettings(self, group, asString=True, reload=False):
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
				"minimize": False
			}
		}

		if reload or not group in self._settings:
			settings = defaults[group] if group in defaults else {}

			self._qsettings.beginGroup(group);
			for setting in self._qsettings.childKeys():
				settings[str(setting)] = self._qsettings.value(setting).toPyObject()
			self._qsettings.endGroup();

			boolSettings = []
			if group == "connection":
				boolSettings += ["ssl", "connect", "join"]
			elif group == "program":
				boolSettings += ["minimize"]

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
			for setting in settings:
				if not isinstance(settings[setting], bool):
					settings[setting] = str(settings[setting]) if settings[setting] else ""

		return settings

	def setSettings(self, group, settings):
		self._settings[group] = settings;

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
		self.statusBar().showMessage(self._("Joining room %s...") % room["name"])

		self._rooms[room["id"]] = {
			"room": None,
			"stream": None,
			"tab": None,
			"editor": None,
			"usersList": None,
			"topicLabel": None,
			"filesLabel": None,
			"newMessages": 0
		}
		self._getWorker().join(room["id"])

	def speak(self):
		message = self._editor.document().toPlainText()
		room = self.getCurrentRoom()
		if not room or message.trimmed().isEmpty():
			return

		self.statusBar().showMessage(self._("Sending message to %s...") % room.name)
		message = str(message)
		self._getWorker().speak(room, message)
		self._editor.document().clear()

	def uploadFile(self):
		print "BROWSE FOR UPLOAD"

	def leaveRoom(self, roomId):
		if roomId in self._rooms:
			self.statusBar().showMessage(self._("Leaving room %s...") % self._rooms[roomId]["room"].name)
			self._getWorker().leave(self._rooms[roomId]["room"])

	def changeTopic(self):
		room = self.getCurrentRoom()
		if not room:
			return
		topic, ok = QtGui.QInputDialog.getText(self,
			self._("Change topic"),
			self._("Enter new topic for room %s") % room.name,
			QtGui.QLineEdit.Normal,
			room.topic
		)
		if ok:
			self.statusBar().showMessage(self._("Changing topic for room %s...") % room.name)
			self._getWorker().changeTopic(room, topic)

	def updateRoomUsers(self, roomId = None):
		if not roomId:
			room = self.getCurrentRoom()
			if room:
				roomId = room.id
		if roomId in self._rooms:
			self.statusBar().showMessage(self._("Getting users in %s...") % self._rooms[roomId]["room"].name)
			self._getWorker().users(self._rooms[roomId]["room"])

	def updateRoomUploads(self, roomId = None):
		if not roomId:
			room = self.getCurrentRoom()
			if room:
				roomId = room.id
		if roomId in self._rooms:
			self.statusBar().showMessage(self._("Getting uploads in %s...") % self._rooms[roomId]["room"].name)
			self._getWorker().uploads(self._rooms[roomId]["room"])

	def getCurrentRoom(self):
		index = self._tabs.currentIndex()
		for roomId in self._rooms.keys():
			if roomId in self._rooms and self._rooms[roomId]["tab"] == index:
				return self._rooms[roomId]["room"]

	def _cfStreamMessage(self, room, message, live=True):
		if (
			not message.user or 
			(live and message.is_text() and message.is_by_current_user()) or
			not room.id in self._rooms
		):
			return

		user = message.user.name
		notify = True
		alert = False

		if message.is_text() and not message.is_by_current_user():
			alert = self._matchesAlert(message.body)

		html = None
		if message.is_joining():
			html = "<font color=\"#%s\">" % self.COLORS["join"]
			html += "--&gt; %s joined %s" % (user, room.name)
			html += "</font>"
		elif message.is_leaving():
			html = "<font color=\"#%s\">" % self.COLORS["leave"]
			html += "&lt;-- %s has left %s" % (user, room.name)
			html += "</font>"
		elif message.is_text():
			body = self._plainTextToHTML(message.tweet["tweet"] if message.is_tweet() else message.body)
			if message.is_tweet():
				body = "<a href=\"%s\">%s</a> <a href=\"%s\">tweeted</a>: %s" % (
					"http://twitter.com/%s" % message.tweet["user"],
					message.tweet["user"], 
					message.tweet["url"],
					body
				)
			elif message.is_paste():
				body = "<br /><hr /><code>%s</code><hr />" % body
			else:
				body = self._autoLink(body)

			created = QtCore.QDateTime(
				message.created_at.year,
				message.created_at.month,
				message.created_at.day,
				message.created_at.hour,
				message.created_at.minute,
				message.created_at.second
			)
			created.setTimeSpec(QtCore.Qt.UTC)

			createdFormat = "h:mm ap"
			if created.daysTo(QtCore.QDateTime.currentDateTime()):
				createdFormat = "MMM d,  %s" % createdFormat

			html = "<font color=\"#%s\">[%s]</font> " % (self.COLORS["time"], created.toLocalTime().toString(createdFormat))

			if alert:
				html += "<font color=\"#%s\">" % self.COLORS["alert"]
			else:
				html += "<font color=\"#%s\">" % self.COLORS["message"]

			if message.is_by_current_user():
				html += "<font color=\"#%s\">" % self.COLORS["nickSelf"]
			elif alert:
			 	html += "<font color=\"#%s\">" % self.COLORS["nickAlert"]
			else:
				html += "<font color=\"#%s\">" % self.COLORS["nick"]

			html += "%s" % ("<strong>%s</strong>" % user if alert else user)
			html += "</font>: "
			html += body
			html += "</font>"
		elif message.is_upload():
			html = "<font color=\"#%s\">" % self.COLORS["upload"]
			html += "<strong>%s</strong> uploaded <a href=\"%s\">%s</a>" % (
				user,
				message.upload["url"],
				message.upload["name"]
			)
			html += "</font>"
		elif message.is_topic_change():
			html = "<font color=\"#%s\">" % self.COLORS["leave"]
			html += "%s changed topic to <strong>%s</strong>" % (user, message.body)
			html += "</font>"

		if html:
			html = "%s<br />" % html
			editor = self._rooms[room.id]["editor"]
			if not editor:
				return

			scrollbar = editor.verticalScrollBar()
			currentScrollbarValue = scrollbar.value()
			autoScroll = (currentScrollbarValue == scrollbar.maximum())
			editor.moveCursor(QtGui.QTextCursor.End)
			editor.textCursor().insertHtml(html)
			if autoScroll:
				scrollbar.setValue(scrollbar.maximum())
			else:
				scrollbar.setValue(currentScrollbarValue)

			tabIndex = self._rooms[room.id]["tab"]
			tabBar = self._tabs.tabBar()
			isActiveTab = (self.isActiveWindow() and tabIndex == self._tabs.currentIndex())

			if message.is_text() and not isActiveTab:
				self._rooms[room.id]["newMessages"] += 1

			if self._rooms[room.id]["newMessages"] > 0:
				tabBar.setTabText(tabIndex, "%s (%s)" % (room.name, self._rooms[room.id]["newMessages"]))

			if not isActiveTab and (alert or self._rooms[room.id]["newMessages"] > 0) and tabBar.tabTextColor(tabIndex) == self.COLORS["tabs"]["normal"]:
				tabBar.setTabTextColor(tabIndex, self.COLORS["tabs"]["alert" if alert else "new"])

			if alert:
				if not isActiveTab:
					self._trayIcon.alert()
				if notify:
					self._notify(room, message.body)

		if (message.is_joining() or message.is_leaving()) and live:
			self.updateRoomUsers(room.id)
		elif message.is_upload() and live:
			self.updateRoomUploads(room.id)
		elif message.is_topic_change() and not message.is_by_current_user():
			self._cfTopicChanged(room, message.body)

	def _matchesAlert(self, message):
		matches = False
		regexes = []
		words = [
			"Mariano Iglesias",
			"Mariano",
			"apple",
			"git",
			"linux"
		]
		for word in words:
			regexes.append("\\b%s\\b" % word)

		for regex in regexes:
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

		self.statusBar().showMessage(self._("%s connected to Campfire") % user.name, 5000)
		self._updateLayout()

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
		self._connecting = False
		self._connected = False
		self._rooms = {}
		self._worker = None
		self.statusBar().clearMessage()

	def _cfRoomJoined(self, room):
		index, editor, usersList, topicLabel, filesLabel = self._setupRoomUI(room)
		self._rooms[room.id]["room"] = room
		self._rooms[room.id]["tab"] = index
		self._rooms[room.id]["editor"] = editor
		self._rooms[room.id]["usersList"] = usersList
		self._rooms[room.id]["topicLabel"] = topicLabel
		self._rooms[room.id]["filesLabel"] = filesLabel
		self._rooms[room.id]["stream"] = self._worker.getStream(room)
		self.updateRoomUsers(room.id)
		self.updateRoomUploads(room.id)
		self.statusBar().showMessage(self._("Joined room %s") % room.name, 5000)
		self._updatedRoomsList()

	def _cfSpoke(self, room, message):
		self._cfStreamMessage(room, message, live=False)
		self.statusBar().clearMessage()

	def _cfRoomLeft(self, room):
		if self._rooms[room.id]["stream"]:
			self._rooms[room.id]["stream"].stop().join()
		self._tabs.removeTab(self._rooms[room.id]["tab"])
		del self._rooms[room.id]
		self.statusBar().showMessage(self._("Left room %s") % room.name, 5000)
		self._updatedRoomsList()

	def _cfRoomUsers(self, room, users):
		# We may be disconnecting while still processing the list
		if not room.id in self._rooms:
			return

		self.statusBar().clearMessage()
		self._rooms[room.id]["usersList"].clear()
		for user in users:
			item = QtGui.QListWidgetItem(user["name"])
			item.setData(QtCore.Qt.UserRole, user)
			self._rooms[room.id]["usersList"].addItem(item)

	def _cfRoomUploads(self, room, uploads):
		# We may be disconnecting while still processing the list
		if not room.id in self._rooms:
			return

		self.statusBar().clearMessage()
		label = self._rooms[room.id]["filesLabel"]
		if uploads:
			html = ""
			for upload in uploads:
				html += "%s&bull; <a href=\"%s\">%s</a>" % (
					"<br />" if html else "",
					upload["full_url"],
					upload["name"]
				)
			html = "%s<br />%s" % (
				self._("Latest uploads:"),
				html
			)

			label.setText(html)
			if not label.isVisible():
				label.show()
		elif label.isVisible():
			label.setText("")
			label.hide()

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
		QtGui.QMessageBox.critical(self, "Error", str(error))

	def _roomSelected(self, index):
		self._updatedRoomsList(index)

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

		if tabBar.tabTextColor(tabIndex) != self.COLORS["tabs"]["normal"]:
			tabBar.setTabTextColor(tabIndex, self.COLORS["tabs"]["normal"])

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
				room[str(key)] = str(data[key].toString())
		return room

	def _connectWorkerSignals(self, worker):
		self.connect(worker, QtCore.SIGNAL("error(PyQt_PyObject)"), self._cfError)
		self.connect(worker, QtCore.SIGNAL("connected(PyQt_PyObject, PyQt_PyObject)"), self._cfConnected)
		self.connect(worker, QtCore.SIGNAL("connectError(PyQt_PyObject)"), self._cfConnectError)
		self.connect(worker, QtCore.SIGNAL("joined(PyQt_PyObject)"), self._cfRoomJoined)
		self.connect(worker, QtCore.SIGNAL("spoke(PyQt_PyObject, PyQt_PyObject)"), self._cfSpoke)
		self.connect(worker, QtCore.SIGNAL("streamMessage(PyQt_PyObject, PyQt_PyObject, PyQt_PyObject)"), self._cfStreamMessage)
		self.connect(worker, QtCore.SIGNAL("left(PyQt_PyObject)"), self._cfRoomLeft)
		self.connect(worker, QtCore.SIGNAL("users(PyQt_PyObject, PyQt_PyObject)"), self._cfRoomUsers)
		self.connect(worker, QtCore.SIGNAL("uploads(PyQt_PyObject, PyQt_PyObject)"), self._cfRoomUploads)
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

	def _notify(self, room, message):
		raise NotImplementedError("_notify() must be implemented")

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
		topicLabel = ClickableQLabel(room.topic)
		topicLabel.setToolTip(self._("Click here to change room's topic"))
		topicLabel.setWordWrap(True)
		self.connect(topicLabel, QtCore.SIGNAL("clicked()"), self.changeTopic)

		editor = QtGui.QTextBrowser()
		editor.setOpenExternalLinks(True)

		usersLabel = QtGui.QLabel(self._("Users in room:"))

		usersList = QtGui.QListWidget()

		filesLabel = QtGui.QLabel("")
		filesLabel.setOpenExternalLinks(True)
		filesLabel.setWordWrap(True)
		filesLabel.hide()

		uploadButton = QtGui.QPushButton(self._("&Upload new file"))
		self.connect(uploadButton, QtCore.SIGNAL('clicked()'), self.uploadFile)

		leftFrameLayout = QtGui.QVBoxLayout()
		leftFrameLayout.addWidget(topicLabel)
		leftFrameLayout.addWidget(editor)

		rightFrameLayout = QtGui.QVBoxLayout()
		rightFrameLayout.addWidget(usersLabel)
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

		if not self.COLORS["tabs"]["normal"]:
			self.COLORS["tabs"]["normal"] = self._tabs.tabBar().tabTextColor(index)
		else:
			self._tabs.tabBar().setTabTextColor(index, self.COLORS["tabs"]["normal"])

		return index, editor, usersList, topicLabel, filesLabel

	def _setupUI(self):
		self.setWindowTitle(self.NAME)

		self._addMenu()
		self._addToolbar()

		self._tabs = QtGui.QTabWidget()
		self._tabs.setTabsClosable(True)
		self.connect(self._tabs, QtCore.SIGNAL("currentChanged(int)"), self._roomTabFocused)
		self.connect(self._tabs, QtCore.SIGNAL("tabCloseRequested(int)"), self._roomTabClose)

		self._editor = QtGui.QPlainTextEdit()
		self._editor.setFixedHeight(self._editor.fontMetrics().height() * 2)
		self._editor.installEventFilter(SuggesterKeyPressEventFilter(self, Suggester(self._editor)))

		speakButton = QtGui.QPushButton(self._("&Send"))
		self.connect(speakButton, QtCore.SIGNAL('clicked()'), self.speak)

		grid = QtGui.QGridLayout()
		grid.setRowStretch(0, 1)
		grid.addWidget(self._tabs, 0, 0, 1, -1)
		grid.addWidget(self._editor, 1, 0)
		grid.addWidget(speakButton, 1, 1)

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

		self._trayIcon = Systray(self._icon, self)
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
				"about": self._createAction(self._("A&bout"))
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
				action.setIcon(QtGui.QIcon(":/icons/%s" % (icon)))
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

	def _plainTextToHTML(self, string):
		return string.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br />")

	def _autoLink(self, string):
		urlre = re.compile("(\(?https?://[-A-Za-z0-9+&@#/%?=~_()|!:,.;]*[-A-Za-z0-9+&@#/%=~_()|])(\">|</a>)?")
		urls = urlre.findall(string)
		cleanUrls = []
		for url in urls:
			if url[1]:
				continue

			currentUrl = url[0]
			if currentUrl[0] == '(' and currentUrl[-1] == ')':
				currentUrl = currentUrl[1:-1]

			if currentUrl in cleanUrls:
				continue

			cleanUrls.append(currentUrl)
			string = re.sub("(?<!(=\"|\">))" + re.escape(currentUrl),
							"<a href=\"" + currentUrl + "\">" + currentUrl + "</a>",
							string)
		return string

class QSnakefire(QtGui.QMainWindow, Snakefire):
	def __init__(self, parent=None):
		QtGui.QMainWindow.__init__(self, parent)
		Snakefire.__init__(self)

	def toolBar(self):
		toolbar = self.addToolBar(self.NAME)
		return toolbar

	def _notify(self, room, message):
		self._trayIcon.showMessage(room.name, message)

if KDE_ENABLED:
	class KSnakefire(kdeui.KMainWindow, Snakefire):
		def __init__(self, parent=None):
			kdeui.KMainWindow.__init__(self, parent)
			Snakefire.__init__(self)

		def _notify(self, room, message):
			notification = kdeui.KNotification.event(
				"Alert",
				message,
				QtGui.QPixmap(),
				self,
				kdeui.KNotification.CloseWhenWidgetActivated
			)

