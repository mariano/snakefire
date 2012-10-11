import base64
import hashlib
import re
import urllib2

from PyQt4 import QtCore

from urlparse import urlparse

class MessageRenderer(QtCore.QThread):
    MESSAGES = {
        "alert": '<div class="alert"><span class="time">[{time}]</span> <span class="author">{user}</span>: {message}</div>',
        "image": '<span id="{url_md5}" class="upload image"><a href="{url}"><img src="data:image/{type};base64,{data}" title="{name}" {attribs} /></a></span><input type="button" onClick=\'{js}\' value="Toggle Image" />',
        "image_url": '<span id="{url_md5}" class="upload image"><a href="{url}"><img src="{url}" title="{name}" {attribs} /></a></span><input id="hide" type=button onClick=\'{js}\' value="Toggle Image" />',
        "join": '<div class="joined">--&gt; {user} joined {room}</div>',
        "leave": '<div class="left">&lt;-- {user} has left {room}</div>',
        "message_self": '<div class="message"><span class="time">[{time}]</span> <span class="author self">{user}</span>: {message}</div>',
        "no_time_message_self": '<div class="message"><span class="author self">{user}</span>: {message}</div>',
        "message": '<div class="message"><span class="time">[{time}]</span> <span class="author">{user}</span>: {message}</div>',
        "no_time_message": '<div class="message"><span class="author">{user}</span>: {message}</div>',
        "paste": '<div class="paste"><pre>{message}</pre></div>',
        "upload": '<span class="upload"><a href="{url}">{name}</a></span>',
        "link": '<a href="{url}">{name}</a>',
        "topic": '<div class="topic">{user} changed topic to <span class="new_topic">{topic}</span></div>',
        "tweet": '<div class="tweet"><a href="{url_user}">{user}</a> <a href="{url}">tweeted</a>: {message}</div>'
    }

    def __init__(self, apiToken, maximumImageWidth, room, message, live=True, updateRoom=True, showTimestamps=True, alert=False, alertIsDirectPing=False, parent=None):
        super(MessageRenderer, self).__init__(parent)
        self._apiToken = apiToken
        self._maximumImageWidth = maximumImageWidth
        self._room = room
        self._message = message
        self._live = live
        self._updateRoom = updateRoom
        self._showTimestamps = showTimestamps
        self._alert = alert
        self._alertIsDirectPing = alertIsDirectPing

    def run(self):
        html = self.render()
        self.emit(QtCore.SIGNAL("render(PyQt_PyObject, PyQt_PyObject, PyQt_PyObject, PyQt_PyObject, PyQt_PyObject, PyQt_PyObject, PyQt_PyObject)"), html, self._room, self._message, self._live, self._updateRoom, self._alert, self._alertIsDirectPing)

    def needsThread(self):
        return self._message.is_upload() or (self._message.body and self._isInlineLink(self._message.body))

    def render(self):
        html = None
        if self._message.is_joining():
            html = self.MESSAGES["join"].format(user=self._message.user.name, room=self._room.name)
        elif (self._message.is_leaving() or self._message.is_kick()):
            html = self.MESSAGES["leave"].format(user=self._message.user.name, room=self._room.name)
        elif self._message.is_text() or self._message.is_upload():
            if self._message.body:
                body = self._plainTextToHTML(self._message.tweet["tweet"] if self._message.is_tweet() else self._message.body)

            if self._message.is_tweet():
                body = self.MESSAGES["tweet"].format(
                    url_user = "http://twitter.com/{user}".format(user=self._message.tweet["user"]),
                    user = self._message.tweet["user"],
                    url = self._message.tweet["url"],
                    message = body
                )
            elif self._message.is_paste():
                body = self.MESSAGES["paste"].format(message=body)
            elif self._message.is_upload():
                body = self._displayUpload()
            elif self._isInlineLink(body):
                body = self._displayInline(body)
            else:
                body = self._autoLink(body)

            created = QtCore.QDateTime(
                self._message.created_at.year,
                self._message.created_at.month,
                self._message.created_at.day,
                self._message.created_at.hour,
                self._message.created_at.minute,
                self._message.created_at.second
            )
            created.setTimeSpec(QtCore.Qt.UTC)

            createdFormat = "h:mm ap"
            if created.daysTo(QtCore.QDateTime.currentDateTime()):
                createdFormat = "MMM d,  {createdFormat}".format(createdFormat=createdFormat)

            key = "message"
            if self._message.is_by_current_user():
                if self._showTimestamps:
                    key = "message_self"
                else:
                    key = "no_time_message_self"
            elif self._alert:
                key = "alert"
            elif not self._showTimestamps:
                key = "no_time_message"

            html = self.MESSAGES[key].format(
                time = created.toLocalTime().toString(createdFormat),
                user = self._message.user.name,
                message = body
            )
        elif self._message.is_topic_change():
            html = self.MESSAGES["topic"].format(user=self._message.user.name, topic=self._message.body)

        return unicode(html)

    def _displayInline(self, message_url):
        request = urllib2.Request(message_url)

        try:
            response = urllib2.urlopen(request)
        except:
            return self._renderInlineLink(message_url, message_url)

        headers = response.info()
        url = message_url
        if response.getcode == '200':
            url = response.geturl()

        meta = {
            'name': url,
            'type': headers["Content-Type"]
        }

        return self._renderInline(url=url, meta=meta)

    def _displayUpload(self):
        request = urllib2.Request(self._message.upload['url'])
        auth_header = base64.encodestring('{}:{}'.format(self._apiToken, 'X')).replace('\n', '')
        request.add_header("Authorization", "Basic {}".format(auth_header))

        try:
            response = urllib2.urlopen(request)
        except:
            return self._renderInlineLink(self._message.upload['url'], self._message.upload['name'])

        data = response.read()
        meta = {
            'name': self._message.upload['name'],
            'type': self._message.upload['content_type'],
        }

        return self._renderInline(url=self._message.upload['url'], data=data, meta=meta)

    def _renderInline(self, url=None, data=None, meta=None):
        if not url and not data:
            raise Exception("Missing image data")

        if self._isImage(meta["type"], meta["name"]):
            attribs = "style=\"max-width: {maxWidth}px;\" ".format(maxWidth=self._maximumImageWidth)
            if data:
                url_md5 = hashlib.md5(url).hexdigest()
                return self.MESSAGES["image"].format(
                    type = meta["type"],
                    data = base64.encodestring(data),
                    url = url,
                    url_md5 = url_md5,
                    name = meta["name"],
                    js = 'if (document.getElementById("'+url_md5+'").style.visibility == "hidden") { document.getElementById("'+url_md5+'").style.visibility="visible"} else {document.getElementById("'+url_md5+'").style.visibility="hidden"}',
                    attribs = attribs
                )
            else:
                url_md5 = hashlib.md5(url).hexdigest()
                return self.MESSAGES["image_url"].format(
                    url = url,
                    name = meta["name"],
                    url_md5 = url_md5,
                    js = 'if (document.getElementById("'+url_md5+'").style.visibility == "hidden") { document.getElementById("'+url_md5+'").style.visibility="visible"} else {document.getElementById("'+url_md5+'").style.visibility="hidden"}',
                    attribs = attribs
                )

        return self._renderInlineLink(url, meta["name"])

    def _renderInlineLink(self, url, name):
        return self.MESSAGES["link"].format(url = url, name = name)

    def _isImage(self, content_type, name):
        if content_type.startswith("image/"):
            return True
        elif content_type == "application/octet-stream" and re.search(".(gif|jpg|jpeg|png)$", name, re.IGNORECASE):
            return True

        return False

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

    def _isInlineLink(self, string):
        try:
            url = urlparse(string)
            if url.scheme is not '' and url.netloc is not '':
                return True
        except:
            pass

        return False
