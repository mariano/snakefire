#!/usr/bin/env python

'''
Setup file largely inspired by http://gitorious.org/smewt/smewt/blobs/master/setup.py
'''

import os, sys
from setuptools import find_packages, setup

name="Snakefire"
args = dict(name=name,
    version="1.0.3",
    description="A Campfire Desktop client for Linux",
    long_description="""Snakefire is a Linux desktop client for Campfire.""",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],
    keywords='linux campfire chat desktop client',
    author='Mariano Iglesias',
    url='http://snakefire.org',
    license='MIT',
    include_package_data=True,
    zip_safe=True,
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

    class AppInstall(command.install.install):
        def _KDECreateNotifyRc(name):
            print "Installing notification resources..."
            path = os.path.join(str(kdecore.KGlobal.dirs().localkdedir()), "share", "apps", self.distribution.get_name())
            if not os.path.isdir(path):
                os.makedirs(path)
            with open("packaging/linux/snakefire.notifyrc", "r") as i:
                with open(os.path.join(path, "snakefire.notifyrc"), "w") as o:
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
            if os.geteuid() == 0:
                python2 = False
                try:
                    subprocess.check_output(['which', 'python2'], stderr=subprocess.STDOUT)
                    python2 = True
                except subprocess.CalledProcessError:
                    pass

                if python2:
                    easy_install = self.distribution.get_command_class('easy_install')
                    cmd = easy_install(self.distribution, args="x", root=self.root, record=self.record)
                    cmd.ensure_finalized()
                    self._fixPythonBin(os.path.join(cmd.script_dir, "snakefire"))

                if kde:
                    self._KDECreateNotifyRc()

                subprocess.call(['xdg-desktop-menu', 'install', 'packaging/linux/cricava-snakefire.desktop'])
                subprocess.call(['xdg-icon-resource', 'install', '--size', '128', 'resources/snakefire.png', 'cricava-snakefire'])
                if os.path.exists('/usr/bin/update-menus'):
                    subprocess.call(['update-menus'])
                elif os.path.exists('/usr/bin/update-desktop-database'):
                    subprocess.call(['update-desktop-database'])

    args.update(dict(
        cmdclass = { "install": AppInstall }
    ))

setup(**args)
