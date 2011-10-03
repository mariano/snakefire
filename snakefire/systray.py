from PyQt4 import QtCore
from PyQt4 import QtGui

class Systray(QtGui.QSystemTrayIcon):
    def __init__(self, icon, mainFrame, interval=500):
        super(Systray, self).__init__(icon, mainFrame)
        self._mainFrame = mainFrame
        self._icon = icon
        self._interval = 250
        self._iconFrames = [icon, QtGui.QIcon()]
        self.connect(self, QtCore.SIGNAL("activated(QSystemTrayIcon::ActivationReason)"), self.activated)

    def alert(self):
        if self._mainFrame.isActiveWindow() or self.isAlerting():
            return

        self._timer = QtCore.QTimer()
        QtCore.QObject.connect(self._timer, QtCore.SIGNAL("timeout()"), self._timerUpdate)
        self._timer.start(self._interval);

    def isAlerting(self):
        return hasattr(self, "_timer") and self._timer

    def stopAlert(self):
        if not self.isAlerting():
            return

        self._timer.stop()
        self._timer = None
        self.setIcon(self._icon)

        if hasattr(self, "_currentIconFrame"):
            del self._currentIconFrame

    def _timerUpdate(self):
        if self._mainFrame.isActiveWindow():
            self.stopAlert()
            return

        if not hasattr(self, "_currentIconFrame") or self._currentIconFrame == len(self._iconFrames) - 1:
            self._currentIconFrame = 0
        else:
            self._currentIconFrame += 1

        self.setIcon(self._iconFrames[self._currentIconFrame])

    def activated(self, reason):
        if reason != QtGui.QSystemTrayIcon.Context and not self._mainFrame.isVisible():
            if self._mainFrame.isMinimized():
                self._mainFrame.setWindowState(self._mainFrame.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
            self._mainFrame.show()
        else:
            if self.isAlerting():
                self.stopAlert()
