from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4 import QtWebKit

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
        (themeSize, themeSizeOk) = self._themeSizeField.itemData(self._themeSizeField.currentIndex()).toInt()

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
        displaySettings = {
            "theme": self._themeField.itemData(self._themeField.currentIndex()).toString(),
            "size": themeSize if themeSizeOk else 100,
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

    def _themeSelected(self):
        self._themePreview.settings().setUserStyleSheetUrl(QtCore.QUrl.fromLocalFile(":/themes/{theme}.css".format(
            theme = self._themeField.itemData(self._themeField.currentIndex()).toString()
        )))

    def _themeSizeSelected(self):
        (value, ok) = self._themeSizeField.itemData(self._themeSizeField.currentIndex()).toInt()
        if ok:
            self._themePreview.setTextSizeMultiplier(round(float(value) / 100, 1))

    def _setupThemesUI(self, displaySettings):
        # Themes

        children = QtCore.QResource(':/themes').children()
        children.sort()

        currentIndex = None
        index = 0
        for theme in children:
            themeName = str(theme.replace(QtCore.QRegExp('\.css$'), ''))
            self._themeField.addItem(themeName.replace('_', ' ').title(), themeName)
            if themeName == displaySettings["theme"]:
                currentIndex = index
            index += 1

        if currentIndex is not None:
            self._themeField.setCurrentIndex(currentIndex)

        # Theme sizes

        currentIndex = None
        index = 0
        for size in [ x for x in range(50, 160, 10) ]:
            self._themeSizeField.addItem("{n}%".format(n=size), size)
            if size == int(displaySettings["size"]):
                currentIndex = index
            index += 1

        if currentIndex is not None:
            self._themeSizeField.setCurrentIndex(currentIndex)

        # Load preview content

        messages = [
            self._mainFrame.MESSAGES['join'].format(user='John Doe', room='Snakefire'),
            self._mainFrame.MESSAGES['message_self'].format(time='3:33 pm', user='John Doe', message='Hey everyone!'),
            self._mainFrame.MESSAGES['message_self'].format(time='3:33 pm', user='John Doe', message='How are you all doing?'),
            self._mainFrame.MESSAGES['alert'].format(time='3:34 pm', user='Jane Doe', message='Hi John Doe! Nice to see you here'),
            self._mainFrame.MESSAGES['tweet'].format(url_user='#', user='@mgiglesias', url='#', message='Hello world from twitter :)'),
            self._mainFrame.MESSAGES['message_self'].format(time='3:35 pm', user='John Doe', message='Look at this method:'),
            self._mainFrame.MESSAGES['paste'].format(message='def hello(self):<br />  print "Hello World"'),
            self._mainFrame.MESSAGES['topic'].format(user='Jane Doe', topic='Testing Snakefire, and loving it'),
            self._mainFrame.MESSAGES['message'].format(time='3:36 pm', user='Jane Doe', message='Looks good. Now look at this upload:'),
            self._mainFrame.MESSAGES['message'].format(time='3:36 pm', user='Jane Doe', 
                message = self._mainFrame.MESSAGES['upload'].format(url='#', name='my_upload.tar.gz')
            )
        ]

        image = QtGui.QImage(":/icons/join.png")
        buffer = QtCore.QBuffer()
        if buffer.open(QtCore.QIODevice.WriteOnly) and image.save(buffer, 'PNG'):
            messages.extend([
                self._mainFrame.MESSAGES['message_self'].format(time='3:38 pm', user='John Doe', message='Look at this image:'),
                self._mainFrame.MESSAGES['message_self'].format(time='3:38 pm', user='John Doe', message=self._mainFrame.MESSAGES['image'].format(
                    url = '#',
                    type = 'image/png',
                    data = buffer.data().toBase64().data(),
                    name = 'image.png',
                    attribs = ''
                ))
            ])

        messages.extend([
            self._mainFrame.MESSAGES['leave'].format(user='Jane Doe', room='Snakefire'),
            self._mainFrame.MESSAGES['message_self'].format(time='3:37 pm', user='John Doe', message='I guess I am all alone now :('),
        ])

        self._themePreview.page().mainFrame().setHtml("\n".join(messages))
        self._themePreview.show()
        self._themeSelected()
        self._themeSizeSelected()

        self.connect(self._themeField, QtCore.SIGNAL("currentIndexChanged(const QString&)"), self._themeSelected)
        self.connect(self._themeSizeField, QtCore.SIGNAL("currentIndexChanged(const QString&)"), self._themeSizeSelected)

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

        # Alert group
        
        self._notifyOnInactiveTabField = QtGui.QCheckBox(self._mainFrame._("&Notify on inactive messages"), self)
        self._matchesField = QtGui.QLineEdit(self)
        
        alertsGrid = QtGui.QGridLayout()
        alertsGrid.addWidget(self._notifyOnInactiveTabField, 1, 0)
        alertsGrid.addWidget(QtGui.QLabel(self._mainFrame._("Matches:"), self), 2, 0)
        alertsGrid.addWidget(self._matchesField, 2, 1)

        alertsGroupBox = QtGui.QGroupBox(self._mainFrame._("Alerts && Notifications"))
        alertsGroupBox.setLayout(alertsGrid)

        # Theme group

        self._themeField = QtGui.QComboBox(self)
        self._themeSizeField = QtGui.QComboBox(self)
        self._themePreview = QtWebKit.QWebView(self)

        themeSelectorBox = QtGui.QHBoxLayout()
        themeSelectorBox.addWidget(QtGui.QLabel(self._mainFrame._("Theme:")))
        themeSelectorBox.addWidget(self._themeField)
        themeSelectorBox.addWidget(QtGui.QLabel(self._mainFrame._("Text size:")))
        themeSelectorBox.addWidget(self._themeSizeField)
        themeSelectorBox.addStretch(1)

        themeSelectorFrame = QtGui.QWidget()
        themeSelectorFrame.setLayout(themeSelectorBox)

        themeGrid = QtGui.QGridLayout()
        themeGrid.addWidget(themeSelectorFrame, 1, 0)
        themeGrid.addWidget(self._themePreview, 2, 0)

        themeGroupBox = QtGui.QGroupBox(self._mainFrame._("Theme"))
        themeGroupBox.setLayout(themeGrid)

        # Events group

        self._showJoinMessageField = QtGui.QCheckBox(self._mainFrame._("&Show join messages"), self)
        self._showPartMessageField = QtGui.QCheckBox(self._mainFrame._("&Show part messages"), self)
        
        eventsGrid = QtGui.QGridLayout()
        eventsGrid.addWidget(self._showJoinMessageField, 1, 0)
        eventsGrid.addWidget(self._showPartMessageField, 2, 0)

        eventsGroupBox = QtGui.QGroupBox(self._mainFrame._("Display events"))
        eventsGroupBox.setLayout(eventsGrid)

        # Options tab

        optionsBox = QtGui.QVBoxLayout()
        optionsBox.addWidget(connectionGroupBox)
        optionsBox.addWidget(programGroupBox)
        optionsBox.addWidget(alertsGroupBox)
        optionsBox.addStretch(1)

        optionsFrame = QtGui.QWidget()
        optionsFrame.setLayout(optionsBox)

        # Display tab

        displayGrid = QtGui.QGridLayout()
        displayGrid.setSpacing(10)
        displayGrid.addWidget(themeGroupBox, 1, 0)
        displayGrid.addWidget(eventsGroupBox, 2, 0)

        displayFrame = QtGui.QWidget()
        displayFrame.setLayout(displayGrid)

        # Tabs

        tabs = QtGui.QTabWidget()
        tabs.setTabsClosable(False)

        tabs.addTab(optionsFrame, self._mainFrame._("&Program options"))
        tabs.addTab(displayFrame, self._mainFrame._("&Display options"))
         
        # Buttons

        self._okButton = QtGui.QPushButton(self._mainFrame._("&OK"), self)
        self._cancelButton = QtGui.QPushButton(self._mainFrame._("&Cancel"), self)

        self.connect(self._okButton, QtCore.SIGNAL('clicked()'), self.ok)
        self.connect(self._cancelButton, QtCore.SIGNAL('clicked()'), self.cancel)

        # Main layout

        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self._okButton)
        hbox.addWidget(self._cancelButton)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(tabs)
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
        self._sslField.setChecked(connectionSettings["ssl"])
        self._connectField.setChecked(connectionSettings["connect"])
        self._joinField.setChecked(connectionSettings["join"])
        self._minimizeField.setChecked(programSettings["minimize"])
        self._notifyOnInactiveTabField.setChecked(alertsSettings["notify_inactive_tab"])
        self._matchesField.setText(alertsSettings["matches"])

        self._showJoinMessageField.setChecked(displaySettings["show_join_message"])
        self._showPartMessageField.setChecked(displaySettings["show_part_message"])

        self._setupThemesUI(displaySettings)
        self.validate()
