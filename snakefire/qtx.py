from PyQt4 import QtGui
from PyQt4 import QtCore

class ClickableQLabel(QtGui.QLabel):
	def __init__(self, parent=None, flags=QtCore.Qt.WindowFlags()):
		super(ClickableQLabel, self).__init__(parent, flags)
		self._setupUI()

	def __init__(self, text, parent=None, flags=QtCore.Qt.WindowFlags()):
		super(ClickableQLabel, self).__init__(text, parent, flags)
		self._setupUI()

	def mouseReleaseEvent(self, event):
		self.emit(QtCore.SIGNAL("clicked()"))

	def _setupUI(self):
		self.setCursor(QtCore.Qt.PointingHandCursor)

class Suggester(QtCore.QObject):
	def __init__(self, editor):
		super(Suggester, self).__init__()
		self._editor = editor
		self._room = None

	def setRoom(self, room):
		self._room = room

	def suggest(self):
		pattern = QtCore.QRegExp('\w+$')
		cursor = self._editor.textCursor()
		block = cursor.block()
		text = block.text()
		if not self._room or not self._room.users or not text or cursor.hasSelection():
			return False

		blockText = QtCore.QString(text[:cursor.position() - block.position()])
		matchPosition = blockText.indexOf(pattern)
		if matchPosition < 0:
			return False

		word = blockText[matchPosition:]
		if word.trimmed().isEmpty():
			return False

		matchingUserNames = []
		for user in self._room.users:
			if QtCore.QString(user["name"]).startsWith(word, QtCore.Qt.CaseInsensitive):
				matchingUserNames.append(user["name"])

		if len(matchingUserNames) == 1:
			self._replace(cursor, word, matchingUserNames[0] + (": " if matchPosition == 0 else " "))
		else:
			menu = QtGui.QMenu('Suggestions', self._editor)
			for userName in matchingUserNames:
				action = QtGui.QAction(userName, menu)
				action.setData((cursor, word, userName, matchPosition))
				self.connect(action, QtCore.SIGNAL("triggered()"), self._userSelected)
				menu.addAction(action)
			menu.popup(self._editor.mapToGlobal(self._editor.cursorRect().center()))

	def _userSelected(self):
		action = self.sender()
		cursor, word, userName, matchPosition = action.data().toPyObject()
		self._replace(cursor, word, userName + (": " if matchPosition == 0 else " "))
	
	def _replace(self, cursor, word, replacement):
		cursor.beginEditBlock()
		for i in range(len(word)):
			cursor.deletePreviousChar()
		cursor.insertText(replacement)
		cursor.endEditBlock()

class SuggesterKeyPressEventFilter(QtCore.QObject):
	def __init__(self, mainFrame, suggester):
		super(SuggesterKeyPressEventFilter, self).__init__(mainFrame)
		self._mainFrame = mainFrame
		self._suggester = suggester

	def eventFilter(self, widget, event):
		if event.type() == QtCore.QEvent.KeyPress:
			key = event.key()
			if key in [QtCore.Qt.Key_Tab, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
				if key in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
					self._mainFrame.speak()
				elif key == QtCore.Qt.Key_Tab:
					self._suggester.setRoom(self._mainFrame.getCurrentRoom())
					if self._suggester.suggest() == False:
						return False
				return True
		return False

class TabWidgetFocusEventFilter(QtCore.QObject):
	def __init__(self, mainFrame):
		super(TabWidgetFocusEventFilter, self).__init__(mainFrame)
		self._mainFrame = mainFrame

	def eventFilter(self, widget, event):
		if event.type() in [QtCore.QEvent.FocusIn, QtCore.QEvent.WindowActivate]:
			self.emit(QtCore.SIGNAL("tabFocused()"))
		return False
