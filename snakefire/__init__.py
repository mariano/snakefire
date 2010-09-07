import os
import resources

KDE_ENABLED = os.getenv("KDE_FULL_SESSION")
GNOME_ENABLED = os.getenv("GNOME_DESKTOP_SESSION_ID")

if KDE_ENABLED:
	from .mainframe import KSnakefire as Snakefire
elif GNOME_ENABLED:
	from .mainframe import GSnakefire as Snakefire
else:
	from .mainframe import QSnakefire as Snakefire
