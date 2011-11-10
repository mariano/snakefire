#!/usr/bin/env python

'''
Setup file largely inspired by http://gitorious.org/smewt/smewt/blobs/master/setup.py
'''

import os, sys
from setuptools import find_packages, setup

args = dict(name="snakefire",
    version="1.0.4",
    description="A Campfire Desktop client for Linux",
    long_description="""\
Snakefire is a desktop client for Campfire that can run on Linux, and any other
OS that has QT support.""",
    classifiers=[
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Topic :: Communications :: Chat"
    ],
    keywords='linux campfire chat desktop client',
    author='Mariano Iglesias',
    author_email='mgiglesias@gmail.com',
    url='http://snakefire.org',
    license='MIT',
    include_package_data=True,
    packages=find_packages(exclude = [ 'ez_setup', 'examples', 'tests', 'utils' ]),
    install_requires=[
        "pyfire>=0.3.4",
        "pyqt",
        "keyring",
        "pyenchant"
    ],
    scripts=["bin/snakefire"]
)

if sys.platform.find("linux") == 0:
    import re, subprocess
    from setuptools import command

    kde = False
    try:
        subprocess.Popen(["kcheckrunning"]).wait()
        kde = True
    except OSError:
        pass

    if kde:
        from PyKDE4 import kdecore

    class SnakefireInstall(command.install.install):
        user_options = command.install.install.user_options + [
            ('install-menu-in-user-mode', None, 'Run xdg-desktop-menu and xdg-icon-resource in user mode')
        ]
        boolean_options = command.install.install.boolean_options + [
            'install-menu-in-user-mode'
        ]

        def initialize_options(self):
            command.install.install.initialize_options(self)
            self.install_menu_in_user_mode = None

        def _binExists(self, bin):
            try:
                subprocess.check_output(['which', bin], stderr=subprocess.STDOUT)
                return True
            except subprocess.CalledProcessError:
                pass
            return False

        def _KDECreateNotifyRc(self):
            print "Installing notification resources..."
            path = os.path.join(str(kdecore.KGlobal.dirs().localkdedir()), "share", "apps", "Snakefire")
            if not os.path.isdir(path):
                os.makedirs(path)
            with open("packaging/linux/Snakefire.notifyrc", "r") as i:
                with open(os.path.join(path, "Snakefire.notifyrc"), "w") as o:
                    o.write(i.read())
                    o.close()
                i.close()

        def _fixPythonBin(self, file, bin = 'python2'):
            with open(file, "r+") as f:
                print "Fixing python path in {file}".format(file=file)
                contents = re.sub('^{regex}'.format(regex=re.escape('#!/usr/bin/env python')), '#!/usr/bin/env {bin}'.format(bin=bin), f.read())
                f.seek(0)
                f.write(contents)
                f.close()

        def run(self):
            command.install.install.run(self)

            if self._binExists('python2'):
                self._fixPythonBin(os.path.join(self.install_scripts, "snakefire"))

            if kde:
                self._KDECreateNotifyRc()

            menu_mode = None
            if self.install_menu_in_user_mode:
                menu_mode = 'user'
            elif os.geteuid() == 0:
                menu_mode = 'system'

            if menu_mode:
                print "Adding program icon and menu item in {mode} mode".format(mode=menu_mode)

                subprocess.call(['xdg-desktop-menu', 'install', '--mode', menu_mode, 'packaging/linux/cricava-snakefire.desktop'])

                for size in [16, 22, 32, 48, 64, 128]:
                    subprocess.call(['xdg-icon-resource', 'install', '--mode', menu_mode, '--size', str(size), 'resources/icons/snakefire-{size}.png'.format(size=size), 'cricava-snakefire'])

                if self._binExists('update-menus'):
                    subprocess.call(['update-menus'])
                elif self._binExists('update-desktop-database'):
                    subprocess.call(['update-desktop-database'])

    args.update(dict(
        cmdclass = { "install": SnakefireInstall }
    ))

setup(**args)
