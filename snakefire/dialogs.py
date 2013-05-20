from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4 import QtWebKit

from renderers import MessageRenderer
from qtx import ClickableQLabel, IdleTimer, RowPushButton, SpellTextEditor

class AboutDialog(QtGui.QDialog):
    def __init__(self, mainFrame):
        super(AboutDialog, self).__init__(mainFrame)
        self._mainFrame = mainFrame

        self.setWindowTitle(self._mainFrame._("About {name}").format(name=self._mainFrame.NAME))
        self._setupUI()

    def _website(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("http://{url}".format(url=self._mainFrame.DOMAIN)))

    def _setupUI(self):
        label = ClickableQLabel()
        label.setPixmap(QtGui.QPixmap(":/images/snakefire-big.png"))
        label.setAlignment(QtCore.Qt.AlignCenter)
        self.connect(label, QtCore.SIGNAL("clicked()"), self._website)

        urlLabel = QtGui.QLabel("<a href=\"http://{url}\">{name}</a>".format(
            url=self._mainFrame.DOMAIN,
            name=self._mainFrame.DOMAIN
        ))
        urlLabel.setOpenExternalLinks(True)
        websiteBox = QtGui.QHBoxLayout()
        websiteBox.addWidget(QtGui.QLabel(self._mainFrame._("Website:")))
        websiteBox.addWidget(urlLabel)
        websiteBox.addStretch(1)

        twitterLabel = QtGui.QLabel("<a href=\"http://twitter.com/snakefirelinux\">@snakefirelinux</a>")
        twitterLabel.setOpenExternalLinks(True)
        twitterBox = QtGui.QHBoxLayout()
        twitterBox.addWidget(QtGui.QLabel(self._mainFrame._("Twitter:")))
        twitterBox.addWidget(twitterLabel)
        twitterBox.addStretch(1)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        layout.addStretch(0.5)
        layout.addWidget(QtGui.QLabel("<strong>{name} v{version}</strong>".format(
            name=self._mainFrame.NAME,
            version=self._mainFrame.VERSION
        )))
        layout.addStretch(0.5)
        layout.addLayout(websiteBox)
        layout.addLayout(twitterBox)

        # Buttons

        self._okButton = QtGui.QPushButton(self._mainFrame._("&OK"), self)
        self.connect(self._okButton, QtCore.SIGNAL('clicked()'), self.close)

        # Main layout

        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self._okButton)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(layout)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

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

    def add(self, match=None):
        row = self._table.rowCount()
        self._table.insertRow(row)

        column = QtGui.QTableWidgetItem()
        column.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        if match:
            column.setText(match['match'])
        self._table.setItem(row, 0, column)

        checkbox = QtGui.QCheckBox(self._table)
        checkbox.setChecked(match['regex'] if match else False)
        self._table.setCellWidget(row, 1, checkbox)

        button = RowPushButton(row, self._mainFrame._("Delete"), self._table)
        self.connect(button, QtCore.SIGNAL('clicked(int)'), self.delete)
        self._table.setCellWidget(row, 2, button)

        self._table.setCurrentCell(row, 0)

    def delete(self, row):
        self._table.removeRow(row)
        self.validate()

    def validate(self):
        isValid = True
        rowCount = self._table.rowCount()
        for i in range(rowCount):
            match = self._table.item(i, 0).text().trimmed()
            if match.isEmpty():
                isValid = False
                break

        self._addButton.setEnabled(isValid)
        self._okButton.setEnabled(isValid)
        return isValid

    def _save(self):
        matches = []
        for i in range(self._table.rowCount()):
            matches.append({
                'match': str(self._table.item(i, 0).text().trimmed()),
                'regex': self._table.cellWidget(i, 1).isChecked()
            })

        self._mainFrame.setSettings("matches", matches)

        alertsSettings = {
            "notify_ping": self._notifyOnPingField.isChecked(),
            "notify_inactive_tab": self._notifyOnInactiveTabField.isChecked(),
            "notify_blink": self._notifyBlinkField.isChecked(),
            "notify_notify": self._notifyNotifyField.isChecked()
        }
        self._mainFrame.setSettings("alerts", alertsSettings)

    def _setupUI(self):
        self._addButton = QtGui.QPushButton(self._mainFrame._("Add"), self)
        self.connect(self._addButton, QtCore.SIGNAL('clicked()'), self.add)

        addBox = QtGui.QHBoxLayout()
        addBox.addStretch(1)
        addBox.addWidget(self._addButton)

        headers = QtCore.QStringList()
        headers.append(QtCore.QString(self._mainFrame._("Search text")))
        headers.append(QtCore.QString(self._mainFrame._("RegEx")))
        headers.append(QtCore.QString(self._mainFrame._("Delete")))

        self._table = QtGui.QTableWidget(self)
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(headers)
        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)

        tableBox = QtGui.QVBoxLayout()
        tableBox.addWidget(self._table)
        tableBox.addLayout(addBox)

        # Options

        self._notifyOnPingField = QtGui.QCheckBox(self._mainFrame._("Alert me whenever I get a &direct message"), self)
        self._notifyOnInactiveTabField = QtGui.QCheckBox(self._mainFrame._("Notify me of every message sent while I'm &inactive"), self)

        optionsGrid = QtGui.QGridLayout()
        optionsGrid.addWidget(self._notifyOnPingField, 1, 0)
        optionsGrid.addWidget(self._notifyOnInactiveTabField, 2, 0)

        optionsGroupBox = QtGui.QGroupBox(self._mainFrame._("Alerts && Notifications"))
        optionsGroupBox.setLayout(optionsGrid)

        # Methods

        self._notifyBlinkField = QtGui.QCheckBox(self._mainFrame._("&Blink the systray icon when notifying"), self)
        self._notifyNotifyField = QtGui.QCheckBox(self._mainFrame._("Trigger a &Notification using the OS notification system"), self)

        methodsGrid = QtGui.QGridLayout()
        methodsGrid.addWidget(self._notifyBlinkField, 1, 0)
        methodsGrid.addWidget(self._notifyNotifyField, 2, 0)

        methodsGroupBox = QtGui.QGroupBox(self._mainFrame._("Notification methods"))
        methodsGroupBox.setLayout(methodsGrid)

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
        vbox.addLayout(tableBox)
        vbox.addWidget(optionsGroupBox)
        vbox.addWidget(methodsGroupBox)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        # Load settings

        alertsSettings = self._mainFrame.getSettings("alerts")
        matches = self._mainFrame.getSettings("matches")

        self._notifyOnPingField.setChecked(alertsSettings["notify_ping"])
        self._notifyOnInactiveTabField.setChecked(alertsSettings["notify_inactive_tab"])
        self._notifyBlinkField.setChecked(alertsSettings["notify_blink"])
        self._notifyNotifyField.setChecked(alertsSettings["notify_notify"])

        if matches:
            for match in matches:
                self.add(match)

        # Only connect to signal after adding rows

        self.connect(self._table, QtCore.SIGNAL('cellChanged(int,int)'), self.validate)
        self.validate()

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
            not self._passwordField.text().isEmpty() and
            ( not self._awayField.isChecked() or not self._awayMessageField.text().trimmed().isEmpty() )
        )
        self._okButton.setEnabled(isValid)
        awayChecked = self._awayField.isEnabled() and self._awayField.isChecked()
        self._awayTimeField.setEnabled(awayChecked)
        self._awayMessageField.setEnabled(awayChecked)
        self._awayTimeBetweenMessagesField.setEnabled(awayChecked)
        return isValid

    def _save(self):
        (themeSize, themeSizeOk) = self._themeSizeField.itemData(self._themeSizeField.currentIndex()).toInt()
        (awayTime, awayTimeOk) = self._awayTimeField.itemData(self._awayTimeField.currentIndex()).toInt()
        (awayTimeBetweenMessages, awayTimeBetweenMessagesOk) = self._awayTimeBetweenMessagesField.itemData(self._awayTimeBetweenMessagesField.currentIndex()).toInt()

        connectionSettings = {
            "subdomain": str(self._subdomainField.text().trimmed()),
            "user": str(self._usernameField.text().trimmed()),
            "password": str(self._passwordField.text()),
            "ssl": self._sslField.isChecked(),
            "connect": self._connectField.isChecked(),
            "join": self._joinField.isChecked()
        }
        programSettings = {
            "minimize": self._minimizeField.isChecked(),
            "spell_language": self._spellLanguageField.itemData(self._spellLanguageField.currentIndex()).toString(),
            "away": self._awayField.isChecked(),
            "away_time": awayTime if awayTimeOk else 10,
            "away_time_between_messages": awayTimeBetweenMessages if awayTimeBetweenMessagesOk else 5,
            "away_message": str(self._awayMessageField.text().trimmed())
        }
        displaySettings = {
            "theme": self._themeField.itemData(self._themeField.currentIndex()).toString(),
            "size": themeSize if themeSizeOk else 100,
            "show_join_message": self._showJoinMessageField.isChecked(),
            "show_part_message": self._showPartMessageField.isChecked(),
            "show_message_timestamps": self._showMessageTimestampsField.isChecked(),
        }

        self._mainFrame.setSettings("connection", connectionSettings)
        self._mainFrame.setSettings("program", programSettings)
        self._mainFrame.setSettings("display", displaySettings)

    def _themeSelected(self):
        self._themePreview.settings().setUserStyleSheetUrl(QtCore.QUrl("qrc:/themes/{theme}.css".format(
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
            MessageRenderer.MESSAGES['join'].format(user='John Doe', room='Snakefire'),
            MessageRenderer.MESSAGES['message_self'].format(time='3:33 pm', user='John Doe', message='Hey everyone!'),
            MessageRenderer.MESSAGES['message_self'].format(time='3:33 pm', user='John Doe', message='How are you all doing?'),
            MessageRenderer.MESSAGES['alert'].format(time='3:34 pm', user='Jane Doe', message='Hi John Doe! Nice to see you here'),
            MessageRenderer.MESSAGES['tweet'].format(url_user='#', user='@mgiglesias', url='#', message='Hello world from twitter :)'),
            MessageRenderer.MESSAGES['message_self'].format(time='3:35 pm', user='John Doe', message='Look at this method:'),
            MessageRenderer.MESSAGES['paste'].format(message='def hello(self):<br />  print "Hello World"'),
            MessageRenderer.MESSAGES['topic'].format(user='Jane Doe', topic='Testing Snakefire, and loving it'),
            MessageRenderer.MESSAGES['message'].format(time='3:36 pm', user='Jane Doe', message='Looks good. Now look at this upload:'),
            MessageRenderer.MESSAGES['message'].format(time='3:36 pm', user='Jane Doe',
                message = MessageRenderer.MESSAGES['upload'].format(url='#', name='my_upload.tar.gz')
            )
        ]

        image = QtGui.QImage(":/icons/snakefire.png")
        buffer = QtCore.QBuffer()
        if buffer.open(QtCore.QIODevice.WriteOnly) and image.save(buffer, 'PNG'):
            messages.extend([
                MessageRenderer.MESSAGES['message_self'].format(time='3:38 pm', user='John Doe', message='Look at this image:'),
                MessageRenderer.MESSAGES['message_self'].format(time='3:38 pm', user='John Doe', message=MessageRenderer.MESSAGES['image'].format(
                    url = '#',
                    type = 'image/png',
                    data = buffer.data().toBase64().data(),
                    name = 'image.png',
                    url_md5 = '',
                    js='',
                    attribs = ''
                ))
            ])

        messages.extend([
            MessageRenderer.MESSAGES['leave'].format(user='Jane Doe', room='Snakefire'),
            MessageRenderer.MESSAGES['message_self'].format(time='3:37 pm', user='John Doe', message='I guess I am all alone now :('),
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

        spellLanguages = {
            "": self._mainFrame._("No spell check")
        }

        if SpellTextEditor.canSpell():
            for language in SpellTextEditor.languages():
                spellLanguages[language] = language;

        self._connectField = QtGui.QCheckBox(self._mainFrame._("Automatically &connect when program starts"), self)
        self._joinField = QtGui.QCheckBox(self._mainFrame._("&Join last opened channels once connected"), self)
        self._minimizeField = QtGui.QCheckBox(self._mainFrame._("&Minimize to system tray if window is minimized, or closed"), self)
        self._spellLanguageField = QtGui.QComboBox(self)

        spellLanguageBox = QtGui.QHBoxLayout()
        spellLanguageBox.addWidget(QtGui.QLabel(self._mainFrame._("Spell checking:"), self))
        spellLanguageBox.addWidget(self._spellLanguageField)
        spellLanguageBox.addStretch(1)

        programGrid = QtGui.QGridLayout()
        programGrid.addWidget(self._connectField, 1, 0)
        programGrid.addWidget(self._joinField, 2, 0)
        programGrid.addWidget(self._minimizeField, 3, 0)
        programGrid.addLayout(spellLanguageBox, 4, 0)

        programGroupBox = QtGui.QGroupBox(self._mainFrame._("Program settings"))
        programGroupBox.setLayout(programGrid)

        if not SpellTextEditor.canSpell():
            self._spellLanguageField.setEnabled(False)

        # Away group

        awayTimes = {
            5: self._mainFrame._("5 minutes"),
            10: self._mainFrame._("10 minutes"),
            15: self._mainFrame._("15 minutes"),
            30: self._mainFrame._("30 minutes"),
            45: self._mainFrame._("45 minutes"),
            60: self._mainFrame._("1 hour"),
            90: self._mainFrame._("1 and a half hours"),
            120: self._mainFrame._("2 hours")
        }

        awayBetweenTimes = {
            2: self._mainFrame._("2 minutes"),
            5: self._mainFrame._("5 minutes"),
            10: self._mainFrame._("10 minutes"),
            15: self._mainFrame._("15 minutes"),
            30: self._mainFrame._("30 minutes"),
            45: self._mainFrame._("45 minutes"),
            60: self._mainFrame._("1 hour")
        }

        self._awayField = QtGui.QCheckBox(self._mainFrame._("Set me as &away after idle time"), self)
        self._awayTimeField = QtGui.QComboBox(self)
        self._awayMessageField = QtGui.QLineEdit(self)
        self._awayTimeBetweenMessagesField = QtGui.QComboBox(self)

        if IdleTimer.supported():
            self.connect(self._awayField, QtCore.SIGNAL('stateChanged(int)'), self.validate)
            self.connect(self._awayMessageField, QtCore.SIGNAL('textChanged(QString)'), self.validate)
        else:
            self._awayField.setEnabled(False)

        awayTimeBox = QtGui.QHBoxLayout()
        awayTimeBox.addWidget(QtGui.QLabel(self._mainFrame._("Idle Time:"), self))
        awayTimeBox.addWidget(self._awayTimeField)
        awayTimeBox.addWidget(QtGui.QLabel(self._mainFrame._("Wait"), self))
        awayTimeBox.addWidget(self._awayTimeBetweenMessagesField)
        awayTimeBox.addWidget(QtGui.QLabel(self._mainFrame._("before sending consecutive messages"), self))
        awayTimeBox.addStretch(1)

        awayMessageBox = QtGui.QHBoxLayout()
        awayMessageBox.addWidget(QtGui.QLabel(self._mainFrame._("Message:"), self))
        awayMessageBox.addWidget(self._awayMessageField)

        awayBox = QtGui.QVBoxLayout()
        awayBox.addWidget(self._awayField)
        awayBox.addLayout(awayTimeBox)
        awayBox.addLayout(awayMessageBox)

        awayGroupBox = QtGui.QGroupBox(self._mainFrame._("Away mode"))
        awayGroupBox.setLayout(awayBox)

        # Theme group

        self._themeField = QtGui.QComboBox(self)
        self._themeSizeField = QtGui.QComboBox(self)
        self._themePreview = QtWebKit.QWebView(self)
        self._themePreview.setMaximumHeight(300)

        themeSelectorBox = QtGui.QHBoxLayout()
        themeSelectorBox.addWidget(QtGui.QLabel(self._mainFrame._("Theme:")))
        themeSelectorBox.addWidget(self._themeField)
        themeSelectorBox.addWidget(QtGui.QLabel(self._mainFrame._("Text size:")))
        themeSelectorBox.addWidget(self._themeSizeField)
        themeSelectorBox.addStretch(1)

        themeSelectorBox.setContentsMargins(0, 0, 0, 0)
        themeSelectorBox.setSpacing(5)

        themeSelectorFrame = QtGui.QWidget()
        themeSelectorFrame.setLayout(themeSelectorBox)

        themeGrid = QtGui.QGridLayout()
        themeGrid.addWidget(themeSelectorFrame, 1, 0)
        themeGrid.addWidget(self._themePreview, 2, 0)

        themeGroupBox = QtGui.QGroupBox(self._mainFrame._("Theme"))
        themeGroupBox.setLayout(themeGrid)

        # Events group

        self._showJoinMessageField = QtGui.QCheckBox(self._mainFrame._("Show &join messages"), self)
        self._showPartMessageField = QtGui.QCheckBox(self._mainFrame._("Show p&art messages"), self)
        self._showMessageTimestampsField = QtGui.QCheckBox(self._mainFrame._("Show message &timestamps"), self)

        eventsGrid = QtGui.QGridLayout()
        eventsGrid.addWidget(self._showJoinMessageField, 1, 0)
        eventsGrid.addWidget(self._showPartMessageField, 2, 0)
        eventsGrid.addWidget(self._showMessageTimestampsField, 3, 0)

        eventsGroupBox = QtGui.QGroupBox(self._mainFrame._("Display events"))
        eventsGroupBox.setLayout(eventsGrid)

        # Options tab

        optionsBox = QtGui.QVBoxLayout()
        optionsBox.addWidget(connectionGroupBox)
        optionsBox.addWidget(programGroupBox)
        optionsBox.addWidget(awayGroupBox)
        optionsBox.addStretch(1)

        optionsFrame = QtGui.QWidget()
        optionsFrame.setLayout(optionsBox)

        # Display tab

        displayBox = QtGui.QVBoxLayout()
        displayBox.addWidget(themeGroupBox)
        displayBox.addWidget(eventsGroupBox)
        displayBox.addStretch(1)

        displayFrame = QtGui.QWidget()
        displayFrame.setLayout(displayBox)

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

        self._subdomainField.setText(connectionSettings["subdomain"])
        self._usernameField.setText(connectionSettings["user"])
        if connectionSettings["password"]:
            self._passwordField.setText(connectionSettings["password"])
        self._sslField.setChecked(connectionSettings["ssl"])
        self._connectField.setChecked(connectionSettings["connect"])
        self._joinField.setChecked(connectionSettings["join"])
        self._minimizeField.setChecked(programSettings["minimize"])
        self._awayField.setChecked(programSettings["away"])
        self._awayMessageField.setText(programSettings["away_message"])

        self._showJoinMessageField.setChecked(displaySettings["show_join_message"])
        self._showPartMessageField.setChecked(displaySettings["show_part_message"])
        self._showMessageTimestampsField.setChecked(displaySettings["show_message_timestamps"])

        self._setupThemesUI(displaySettings)

        currentIndex = None
        index = 0
        spellLanguageKeys = spellLanguages.keys()
        spellLanguageKeys.sort()
        for value in spellLanguageKeys:
            self._spellLanguageField.addItem(spellLanguages[value], value)
            if value == programSettings["spell_language"]:
                currentIndex = index
            index += 1

        if currentIndex is not None:
            self._spellLanguageField.setCurrentIndex(currentIndex)

        currentIndex = None
        index = 0
        awayTimeKeys = awayTimes.keys()
        awayTimeKeys.sort()
        for value in awayTimeKeys:
            self._awayTimeField.addItem(awayTimes[value], value)
            if value == int(programSettings["away_time"]):
                currentIndex = index
            index += 1

        if currentIndex is not None:
            self._awayTimeField.setCurrentIndex(currentIndex)

        currentIndex = None
        index = 0
        awayBetweenTimeKeys = awayBetweenTimes.keys()
        awayBetweenTimeKeys.sort()
        for value in awayBetweenTimeKeys:
            self._awayTimeBetweenMessagesField.addItem(awayBetweenTimes[value], value)
            if value == int(programSettings["away_time_between_messages"]):
                currentIndex = index
            index += 1

        if currentIndex is not None:
            self._awayTimeBetweenMessagesField.setCurrentIndex(currentIndex)

        self.validate()
