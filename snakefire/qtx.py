import ctypes
import re

from PyQt4 import Qt
from PyQt4 import QtGui
from PyQt4 import QtCore

try:
    import pxss
except:
    pass

try:
    import enchant
except ImportError:
    enchant = None

class SpellTextEditor(Qt.QPlainTextEdit):
    '''A QTextEdit-based editor that supports syntax highlighting and
    spellchecking out of the box

    Greatly based on the work of John Schember <john@nachtimwald.com>
    '''
    MINIMUM_VIEWABLE_LINES = 3
    MAXIMUM_VIEWABLE_LINES = 8

    def __init__(self, lang=True, mainFrame = None, *args):
        super(SpellTextEditor, self).__init__(*args)
        self._mainFrame = mainFrame
        self._dict = None
        self._defaultDict = None
        self._highlighter = None
        if lang:
            self.enableSpell(lang)
        self.setFixedHeight(self.fontMetrics().height() * self.MINIMUM_VIEWABLE_LINES)
        self.installEventFilter(EditorKeyPressEventFilter(mainFrame, self))
        self.connect(self, QtCore.SIGNAL('textChanged()'), self._onTextChanged)

    @staticmethod
    def canSpell():
        can = True if enchant else False
        if can:
            try:
                dict = enchant.Dict()
            except enchant.DictNotFoundError:
                can = False
        return can

    @staticmethod
    def languages():
        return enchant.list_languages() if enchant else None

    @staticmethod
    def defaultLanguage():
        tag = None
        if enchant:
            try:
                tag = enchant.Dict().tag
            except enchant.DictNotFoundError:
                pass
        return tag

    def enableSpell(self, lang=None):
        if SpellTextEditor.canSpell():
            if lang:
                self._dict = enchant.Dict(lang)
            else:
                self._dict = enchant.Dict()
        else:
            self._dict = None

        self._highlighter = SpellHighlighter(self.document())
        if self._dict:
            self._highlighter.setDict(self._dict)
            self._highlighter.rehighlight()

    def disableSpell(self):
        self._dict = None
        if self._highlighter:
            self._highlighter.setDocument(None)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            # Rewrite the mouse event to a left button event so the cursor is
            # moved to the location of the pointer.
            event = Qt.QMouseEvent(Qt.QEvent.MouseButtonPress, event.pos(),
                QtCore.Qt.LeftButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        super(SpellTextEditor, self).mousePressEvent(event)

    def contextMenuEvent(self, event):
        popup_menu = self.createStandardContextMenu()

        cursor = self.textCursor()
        cursor.select(Qt.QTextCursor.WordUnderCursor)
        self.setTextCursor(cursor)

        # Check if the selected word is misspelled and offer spelling
        # suggestions if it is.
        if enchant and self._dict:
            if self.textCursor().hasSelection():
                text = unicode(self.textCursor().selectedText())
                if not self._dict.check(text):
                    spell_menu = Qt.QMenu(self._mainFrame._('Spelling Suggestions') if self._mainFrame else QtCore.QCoreApplication.translate('app', 'Spelling Suggestions'), self)
                    for word in self._dict.suggest(text):
                        action = SpellAction(word, spell_menu)
                        action.correct.connect(self.correctWord)
                        spell_menu.addAction(action)
                    # Only add the spelling suggests to the menu if there are
                    # suggestions.
                    if len(spell_menu.actions()) != 0:
                        popup_menu.insertSeparator(popup_menu.actions()[0])
                        popup_menu.insertMenu(popup_menu.actions()[0], spell_menu)

        popup_menu.exec_(event.globalPos())

    def correctWord(self, word):
        '''
        Replaces the selected text with word.
        '''
        cursor = self.textCursor()
        cursor.beginEditBlock()

        cursor.removeSelectedText()
        cursor.insertText(word)

        cursor.endEditBlock()

    def _onTextChanged(self):
        text = self.document().toPlainText()
        viewableLines = self.height() / self.fontMetrics().height()
        hasNewLine = text.indexOf("\n") > 0
        if (hasNewLine and viewableLines < self.MAXIMUM_VIEWABLE_LINES) or (not hasNewLine and viewableLines > self.MINIMUM_VIEWABLE_LINES):
            viewableLines = self.MAXIMUM_VIEWABLE_LINES if hasNewLine else self.MINIMUM_VIEWABLE_LINES
            self.setFixedHeight(self.fontMetrics().height() * viewableLines)

class SpellHighlighter(Qt.QSyntaxHighlighter):
    WORDS = u'(?iu)[\w\']+'

    def __init__(self, *args):
        super(SpellHighlighter, self).__init__(*args)
        self.dict = None

    def setDict(self, dict):
        self.dict = dict

    def highlightBlock(self, text):
        if not self.dict:
            return

        text = unicode(text)

        format = Qt.QTextCharFormat()
        format.setUnderlineColor(QtCore.Qt.red)
        format.setUnderlineStyle(Qt.QTextCharFormat.DotLine)

        for word_object in re.finditer(self.WORDS, text):
            if not self.dict.check(word_object.group()):
                self.setFormat(word_object.start(),
                    word_object.end() - word_object.start(), format)

class SpellAction(Qt.QAction):
    '''
    A special QAction that returns the text in a signal.
    '''

    correct = QtCore.pyqtSignal(unicode)

    def __init__(self, *args):
        super(SpellAction, self).__init__(*args)
        self.triggered.connect(lambda x: self.correct.emit(
            unicode(self.toolTip())))

class IdleTimer(QtCore.QThread):
    def __init__(self, parent, idleSeconds):
        super(IdleTimer, self).__init__(parent)

        if not self.supported():
            raise OSError("IdleTimer not supported on this system")

        self._idleSeconds = idleSeconds
        self._finish = False
        self._mutex = QtCore.QMutex()
        self._tracker = pxss.IdleTracker(idle_threshold = idleSeconds * 1000)

    @staticmethod
    def supported():
        supported = False
        for lib in ['libXss.so', 'libXss.so.1']:
            try:
                if ctypes.CDLL(lib):
                    supported = True
                    break
            except OSError:
                pass
        return supported

    def stop(self):
        self._mutex.lock()
        self._finish = True
        self._mutex.unlock()

    def run(self):
        isIdle = False
        while not self._finish:
            (state, nextCheck, idle) = self._tracker.check_idle()

            if state == 'idle' and not isIdle and idle >= (self._idleSeconds * 1000):
                self.emit(QtCore.SIGNAL("idle()"))
            elif state is not None and isIdle:
                self.emit(QtCore.SIGNAL('active()'))

            if state is not None:
                isIdle = (state == 'idle')

            self.usleep(nextCheck * 1000)

class RowPushButton(QtGui.QPushButton):
    def __init__(self, row, text, parent=None):
        super(RowPushButton, self).__init__(parent)
        self._row = row
        self.setIcon(self.style().standardIcon(self.style().SP_TrashIcon))
        self.setToolTip(text)
        self.connect(self, QtCore.SIGNAL("clicked()"), self._clicked)

    def _clicked(self):
        self.emit(QtCore.SIGNAL("clicked(int)"), self._row)

class ClickableQLabel(QtGui.QLabel):
    def __init__(self, text=None, parent=None, flags=QtCore.Qt.WindowFlags()):
        if text:
            super(ClickableQLabel, self).__init__(text, parent, flags)
        else:
            super(ClickableQLabel, self).__init__(parent, flags)

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

class EditorKeyPressEventFilter(QtCore.QObject):
    def __init__(self, mainFrame, editor):
        super(EditorKeyPressEventFilter, self).__init__(mainFrame)
        self._mainFrame = mainFrame
        self._editor = editor
        self._suggester = Suggester(self._editor)

    def eventFilter(self, widget, event):
        if event.type() == QtCore.QEvent.KeyPress:
            key = event.key()
            if key == QtCore.Qt.Key_Tab:
                self._suggester.setRoom(self._mainFrame.getCurrentRoom())
                if self._suggester.suggest() != False:
                    return True
            elif key in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
                if event.modifiers() & QtCore.Qt.ShiftModifier:
                    return False
                self._mainFrame.speak()
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
