import os, resources, subprocess
import dbus, dbus.proxies

NOTIFICATIONS_ENABLED = False
KDE_ENABLED = False

try:
    subprocess.Popen(["kcheckrunning"]).wait()
    KDE_ENABLED = True
except OSError:
    pass

try:
    dbus.proxies.ProxyObject(conn=dbus.SessionBus(),
                             bus_name="org.freedesktop.Notifications",
                             object_path="/org/freedesktop/Notifications")
    NOTIFICATIONS_ENABLED = True
except dbus.exceptions.DBusException:
    pass

if KDE_ENABLED:
    from .mainframe import KSnakefire as Snakefire
elif NOTIFICATIONS_ENABLED:
    from .mainframe import GSnakefire as Snakefire
else:
    from .mainframe import QSnakefire as Snakefire
