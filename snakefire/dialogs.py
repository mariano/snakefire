from PyQt4 import QtCore
from PyQt4 import QtGui

class AlertsDialog(QtGui.QDialog):
    def __init__(self, mainFrame):
        super(AlertsDialog, self).__init__(mainFrame)
        self._mainFrame = mainFrame

        self.setWindowTitle(self._mainFrame._("Alerts"))
        self._setupUI()

    def ok(self):
        self._save()
        self.close()

    def cancel(self):
        self.close()

    def _setupUI(self):
        pass

class OptionsDialog(QtGui.QDialog):
    def __init__(self, mainFrame):
        super(OptionsDialog, self).__init__(mainFrame)
        self._mainFrame = mainFrame

        self.setWindowTitle(self._mainFrame._("Settings"))
        self._setupUI()

    def ok(self):
        self._save()
        self.close()

    def cancel(self):
        self.close()

    def validate(self):
        isValid = (
            not self._subdomainField.text().trimmed().isEmpty() and
            not self._usernameField.text().trimmed().isEmpty() and
            not self._passwordField.text().isEmpty()
        )
        self._okButton.setEnabled(isValid)
        return isValid

    def _save(self):
        connectionSettings = {
            "subdomain": str(self._subdomainField.text().trimmed()),
            "user": str(self._usernameField.text().trimmed()),
            "password": str(self._passwordField.text()),
            "api_auth_token": str(self._apiAuthTokenField.text().trimmed()),
            "ssl": self._sslField.isChecked(),
            "connect": self._connectField.isChecked(),
            "join": self._joinField.isChecked()
        }
        programSettings = {
            "minimize": self._minimizeField.isChecked()
        }
        displaySettings = {
            "show_join_message": self._showJoinMessageField.isChecked(),
            "show_part_message": self._showPartMessageField.isChecked()
        }
        alertsSettings = {
            "notify_inactive_tab": self._notifyOnInactiveTabField.isChecked(),
            "matches": str(self._matchesField.text().trimmed())
        }

        self._mainFrame.setSettings("connection", connectionSettings)
        self._mainFrame.setSettings("program", programSettings)
        self._mainFrame.setSettings("display", displaySettings)
        self._mainFrame.setSettings("alerts", alertsSettings)

    def _setupUI(self):
        # Connection group

        self._subdomainField = QtGui.QLineEdit(self)
        self._usernameField = QtGui.QLineEdit(self)
        self._passwordField = QtGui.QLineEdit(self)
        self._passwordField.setEchoMode(QtGui.QLineEdit.Password)
        self._apiAuthTokenField = QtGui.QLineEdit(self)
        self._sslField = QtGui.QCheckBox(self._mainFrame._("Use &secure connection (SSL)"), self)

        self.connect(self._subdomainField, QtCore.SIGNAL('textChanged(QString)'), self.validate)
        self.connect(self._usernameField, QtCore.SIGNAL('textChanged(QString)'), self.validate)
        self.connect(self._passwordField, QtCore.SIGNAL('textChanged(QString)'), self.validate)

        connectionGrid = QtGui.QGridLayout()
        connectionGrid.addWidget(QtGui.QLabel(self._mainFrame._("Subdomain:"), self), 1, 0)
        connectionGrid.addWidget(self._subdomainField, 1, 1)
        connectionGrid.addWidget(QtGui.QLabel(self._mainFrame._("Username:"), self), 2, 0)
        connectionGrid.addWidget(self._usernameField, 2, 1)
        connectionGrid.addWidget(QtGui.QLabel(self._mainFrame._("Password:"), self), 3, 0)
        connectionGrid.addWidget(self._passwordField, 3, 1)
        connectionGrid.addWidget(QtGui.QLabel(self._mainFrame._("API Auth Token:"), self), 4, 0)
        connectionGrid.addWidget(self._apiAuthTokenField, 4, 1)
        connectionGrid.addWidget(self._sslField, 5, 0, 1, -1)

        connectionGroupBox = QtGui.QGroupBox(self._mainFrame._("Campfire connection"))
        connectionGroupBox.setLayout(connectionGrid)

        # Program group
        
        self._connectField = QtGui.QCheckBox(self._mainFrame._("Automatically &connect when program starts"), self)
        self._joinField = QtGui.QCheckBox(self._mainFrame._("&Join last opened channels once connected"), self)
        self._minimizeField = QtGui.QCheckBox(self._mainFrame._("&Minimize to system tray if window is minimized, or closed"), self)

        programGrid = QtGui.QGridLayout()
        programGrid.addWidget(self._connectField, 1, 0)
        programGrid.addWidget(self._joinField, 2, 0)
        programGrid.addWidget(self._minimizeField, 3, 0)

        programGroupBox = QtGui.QGroupBox(self._mainFrame._("Program settings"))
        programGroupBox.setLayout(programGrid)

        # Display group
        self._showJoinMessageField = QtGui.QCheckBox(self._mainFrame._("&Show join messages"), self)
        self._showPartMessageField = QtGui.QCheckBox(self._mainFrame._("&Show part messages"), self)
        
        displayGrid = QtGui.QGridLayout()
        displayGrid.addWidget(self._showJoinMessageField, 1, 0)
        displayGrid.addWidget(self._showPartMessageField, 2, 0)

        displayGroupBox = QtGui.QGroupBox(self._mainFrame._("Display settings"))
        displayGroupBox.setLayout(displayGrid)

        # Alert group
        
        self._notifyOnInactiveTabField = QtGui.QCheckBox(self._mainFrame._("&Notify on inactive messages"), self)
        self._matchesField = QtGui.QLineEdit(self)
        
        alertsGrid = QtGui.QGridLayout()
        alertsGrid.addWidget(self._notifyOnInactiveTabField, 1, 0)
        alertsGrid.addWidget(QtGui.QLabel(self._mainFrame._("Matches:"), self), 2, 0)
        alertsGrid.addWidget(self._matchesField, 2, 1)

        alertsGroupBox = QtGui.QGroupBox(self._mainFrame._("Alerts & Notifications"))
        alertsGroupBox.setLayout(alertsGrid)
         
        # Buttons

        self._okButton = QtGui.QPushButton(self._mainFrame._("&OK"), self)
        self._cancelButton = QtGui.QPushButton(self._mainFrame._("&Cancel"), self)

        self.connect(self._okButton, QtCore.SIGNAL('clicked()'), self.ok)
        self.connect(self._cancelButton, QtCore.SIGNAL('clicked()'), self.cancel)

        # Main layout

        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        grid.addWidget(connectionGroupBox, 1, 0)
        grid.addWidget(programGroupBox, 2, 0)
        grid.addWidget(displayGroupBox, 3, 0)
        grid.addWidget(alertsGroupBox, 4, 0)

        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self._okButton)
        hbox.addWidget(self._cancelButton)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(grid)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

        # Load settings

        connectionSettings = self._mainFrame.getSettings("connection")
        programSettings = self._mainFrame.getSettings("program")
        displaySettings = self._mainFrame.getSettings("display")
        alertsSettings = self._mainFrame.getSettings("alerts")

        self._subdomainField.setText(connectionSettings["subdomain"])
        self._usernameField.setText(connectionSettings["user"])
        if connectionSettings["password"]:
            self._passwordField.setText(connectionSettings["password"])
        self._apiAuthTokenField.setText(connectionSettings["api_auth_token"])
        self._sslField.setChecked(connectionSettings["ssl"])
        self._connectField.setChecked(connectionSettings["connect"])
        self._joinField.setChecked(connectionSettings["join"])
        self._minimizeField.setChecked(programSettings["minimize"])
        self._showJoinMessageField.setChecked(displaySettings["show_join_message"])
        self._showPartMessageField.setChecked(displaySettings["show_part_message"])
        self._notifyOnInactiveTabField.setChecked(alertsSettings["notify_inactive_tab"])
        self._matchesField.setText(alertsSettings["matches"])

        self.validate()
