#!/usr/bin/env python

print("ERROR: Automatic setup is NOT ready. To run Snakefire manually, \
read the 'BETA TESTING: Running without installation' section in the \
README file.")
exit()

import os

from setuptools import setup

home = os.path.expanduser("~")
if home == "~":
    raise Exception("Can't find user directory")

name="Snakefire"
icon="codeblocks.png"
setup(name=name,
    version="1.0.1",
    description="A Campfire Desktop client for Linux (KDE)",
    long_description="""Snakefire is a native desktop client for KDE for Campfire.""",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],
    keywords='linux kde campfire chat',
    author='Mariano Iglesias',
    url='http://snakefire.org',
    license='MIT',
    include_package_data=True,
    zip_safe=True,
    requires=['pyfire (>=0.3.0)'],
    scripts=["snakefire.py"],
    data_files=[
        ("%s/.kde/share/apps/%s" % (home, name), ["resources/Snakefire.notifyrc"]),
        ("", [icon, "snakefire.desktop"])
    ]
)
