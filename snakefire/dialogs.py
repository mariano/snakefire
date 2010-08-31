from PyQt4 import QtCore
from PyQt4 import QtGui

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
			"ssl": self._sslField.isChecked(),
			"connect": self._connectField.isChecked(),
			"join": self._joinField.isChecked()
		}
		programSettings = {
			"minimize": self._minimizeField.isChecked()
		}
		self._mainFrame.setSettings("connection", connectionSettings)
		self._mainFrame.setSettings("program", programSettings)

	def _setupUI(self):
		# Connection group

		self._subdomainField = QtGui.QLineEdit(self)
		self._usernameField = QtGui.QLineEdit(self)
		self._passwordField = QtGui.QLineEdit(self)
		self._passwordField.setEchoMode(QtGui.QLineEdit.Password)
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
		connectionGrid.addWidget(self._sslField, 4, 0, 1, -1)

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

		self._subdomainField.setText(connectionSettings["subdomain"])
		self._usernameField.setText(connectionSettings["user"])
		if connectionSettings["password"]:
			self._passwordField.setText(connectionSettings["password"])
		self._sslField.setChecked(connectionSettings["ssl"])
		self._connectField.setChecked(connectionSettings["connect"])
		self._joinField.setChecked(connectionSettings["join"])
		self._minimizeField.setChecked(programSettings["minimize"])

		self.validate()
