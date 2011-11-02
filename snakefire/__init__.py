import os, resources, subprocess

GNOME_ENABLED = os.getenv("GNOME_DESKTOP_SESSION_ID")
XFCE_ENABLED = os.getenv("XDG_SESSION_COOKIE")
KDE_ENABLED = False

try:
    subprocess.Popen(["kcheckrunning"]).wait()
    KDE_ENABLED = True
except OSError:
    pass


if KDE_ENABLED:
    from .mainframe import KSnakefire as Snakefire
elif GNOME_ENABLED or XFCE_ENABLED:
    from .mainframe import GSnakefire as Snakefire
else:
    from .mainframe import QSnakefire as Snakefire
