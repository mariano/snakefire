# Snakefire: Campfire Desktop client for Linux #

## LICENSE ##

Pyfire is released under the [MIT License] [license].

## TEAM ##

* Mariano Iglesias - [@mgiglesias] [twitter_mgiglesias] | [marianoiglesias.com.ar] [website_mgiglesias]
* Zak Zajac - [@madzak] [twitter_madzak] | [madzak.com] [website_madzak]

## INSTALLATION ##

### Requirements ###

### PyQT4 ###

The python library for QT is required.

For *Ubuntu based* systems, PyQT4 is in the official repositories, and can be
installed the following way:

		$ sudo apt-get install python-qt4

For *Arch Linux*, PyQT4 is in the extra repository, and can be installed with:

		$ pacman -S pyqt

Other OS should refer to the [PyQT4 download page] [pyqt-download]

#### Keyring ####

For *Ubuntu based* systems, Keyring is in the official repositories, and can be
installed the following way:

1. For Ubuntu (GNOME) or Kubuntu (KDE):

		$ sudo apt-get install python-keyring

For *Arch Linux*, Keyring is in an AUR repository. If you have [yaourt] [yaourt],
you can install it with (if you don't have yaourt, you should really 
[get it] [yaourt]

		$ yaourt -S python-keyring

Other OS should read [Python Keyring installation docs] [keyring-install].

All *XFCE* users should install GNOME keyring.

#### PyOpenSSL ####

For *Ubuntu based* systems, PyOpenSSL is in the official repositories, and can be
installed the following way:

		$ sudo apt-get install python-openssl

For *Arch Linux*, PyOpenSSL is in the extra repository, and can be installed with:

		$ pacman -S pyopenssl

Other OS should read [PyOpenSSL download page] [pyopenssl-download].

#### Notifications ####

For *Ubuntu based* systems, python-notify is in the official repositores, and can be
installed the following way:

        $ sudo apt-get install python-notify

For *Arch Linux*, python-notify is in the extra repository, and can be installed with:

        $ pacman -S python-notify

#### Twisted ####

For *Ubuntu based* systems, Twisted is in the official repositories, and can be
installed the following way:

*Ubuntu Lucid (10.04)*: the version included in the official repositories (10.0)
is older than what Pyfire requires. You can use twisted PPA's repository
instead, and install Twisted:

		$ sudo add-apt-repository ppa:twisted-dev/ppa
		$ sudo apt-get update
		$ sudo apt-get install python-twisted

*Ubuntu Maverick (10.10)*: the version included is what Pyfire requires, so
Twisted can be easily installed with:

		$ sudo apt-get install python-twisted

For *Arch Linux*, Twisted is in the extra repository and can be installed with:

		$ pacman -S twisted

Other OS should refer to the [Twisted download page] [twisted-download] which
shows how to install Twisted on several platforms. 

#### Python Imaging Library ####


For *Ubuntu based* systems, PIL is in the official repositories, and can be
installed the following way:

        $ sudo apt-get install python-imaging

For *Arch Linux*, PIL is in the extra repository and can be installed with:

        $ pacman -S python-imaging

### Installing Snakefire ###

#### Running the developer version ####

If you wish to run the latest version of Snakefire, without having to
explicitly install it, follow these instructions:

1. Get the latest development version by cloning from its GIT repository:

		$ git clone git://github.com/mariano/snakefire
		$ cd snakefire
		$ git submodule init
		$ git submodule update

   You can keep up with the latest updates by accessing the directory where
   you installed Snakefire, and running:

		$ git pull --rebase

2. If you are on *KDE*, install the notify configuration to your home directory
   by running the following commands from the directory where you installed
   Snakefire:

		$ export KDE_LOCAL_PREFIX=`kde4-config --localprefix`
		$ mkdir -p $KDE_LOCAL_PREFIX/share/apps/Snakefire
		$ cp resources/*.notifyrc $KDE_LOCAL_PREFIX/share/apps/Snakefire
		$ killall knotify4

You are now ready to run Snakefire. Enter the directory where you installed
Snakefire, and do:

	For *Arch Linux*, you have to use python2:

		$ python2 snakefire.py

	For other OS, do:

		$ python snakefire.py

[license]: http://www.opensource.org/licenses/mit-license.php
[pyqt-download]: http://www.riverbankcomputing.co.uk/software/pyqt/download
[pyfire-readme]: http://github.com/mariano/pyfire#readme
[yaourt]: http://wiki.archlinux.org/index.php/Yaourt
[keyring-install]: http://pypi.python.org/pypi/keyring/#installation-instructions
[pyopenssl-download]: http://pypi.python.org/pypi/pyOpenSSL
[twisted]: http://twistedmatrix.com
[twisted-download]: http://twistedmatrix.com/trac/wiki/Downloads
[twitter_mgiglesias]: http://twitter.com/mgiglesias
[website_mgiglesias]: http://marianoiglesias.com.ar
[twitter_madzak]: http://twitter.com/madzak
[website_madzak]: http://www.madzak.com

