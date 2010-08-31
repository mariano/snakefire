import os

KDE_ENABLED = os.getenv("KDE_FULL_SESSION")

if KDE_ENABLED:
	from .mainframe import KSnakefire as Snakefire
else:
	from .mainframe import QSnakefire as Snakefire
