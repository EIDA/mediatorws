Installing the EIDA NG webservices for development usage
========================================================

In order to develop with the EIDA NG webservices an installation from source
must be performed. The installation is performed by means of the `virtualenv
<https://pypi.python.org/pypi/virtualenv>`_ package.

.. note::

  This installation method currently only is prepared for the EIDA Federator
  and StationLite webservices.


First of all, choose an installation directory:

.. code::

  $ export PATH_INSTALLATION_DIRECTORY=$HOME/work

Dependencies
^^^^^^^^^^^^

Make sure the following software is installed:

  * `libxml2 <http://xmlsoft.org/>`_
  * `libxslt <http://xmlsoft.org/XSLT/>`_

Regarding the version to be used visit http://lxml.de/installation.html#requirements.

To install the required development packages of these dependencies on Linux
systems, use your distribution specific installation tool, e.g. apt-get on
Debian/Ubuntu:

.. code::

  $ sudo apt-get install libxml2-dev libxslt-dev python-dev

Download
^^^^^^^^

From the `EIDA GitHub <https://github.com/EIDA/mediatorws>`_ download a copy of
the *mediatorws* source code:

.. code::

  $ cd $PATH_INSTALLATION_DIRECTORY
  $ git clone https://github.com/EIDA/mediatorws

Installing *virtualenv*
^^^^^^^^^^^^^^^^^^^^^^^

In case *virtualenv* is not available yet, install the package via pip:

.. code::

  # pip install virtualenv

Test your *virtualenv* installation:

.. code::

  $ virtualenv --version

Create a virtual environment for the EIDA NG webservices. Use the :code:`-p
/path/to/python` to setup your virtual environment with the corresponding
python interpreter. The EIDA NG webservices both run with Python 2.7 and Python
3.4+.

.. code::

  $ cd $PATH_INSTALLATION_DIRECTORY/mediatorws
  $ virtualenv venv

.. note::

  When using a Python virtual environment with *mod_wsgi*, it is very important
  that it has been created using the same Python installation that *mod_wsgi*
  was originally compiled for. It is **not** possible to use a Python virtual
  environment to force *mod_wsgi* to use a different Python version, or even a
  different Python installation.

To activate your brand new virtual environment use

.. code::

  $ . $PATH_INSTALLATION_DIRECTORY/mediatorws/venv/bin/activate

When you are done disable it:

.. code::

  (venv) $ deactivate

Install
^^^^^^^

EIDA NG webservices provide simple and reusable installation routines. After
activating the virtual environment with

.. code::

  $ . $PATH_INSTALLATION_DIRECTORY/mediatorws/venv/bin/activate


execute:

.. code::

  (venv) $ cd $PATH_INSTALLATION_DIRECTORY/mediatorws/ 
  (venv) $ make ls

A list of available :code:`SERVICES` is displayed. Choose the EIDA NG service
you would like to install

.. code::

  (venv) $ export MY_EIDA_SERVICES="list of EIDA NG services"

Next, enter

.. code::

  (venv) $ make install SERVICES="$MY_EIDA_SERVICES"

to install the EIDA NG webservices chosen. Alternatively run

.. code::

  (venv) $ make install 

to install all services available. Besides of the webservices specified the
command will resolve, download and install all dependencies necessary.

Finally test your webservice installations. To test for example the *federator*
webservice installation enter

.. code::

  (venv) $ eida-federator -V

The version of your *federator* installation should be displayed. Now you are
ready to launch the `Test WSGI servers <#Run the Test WSGI Servers>`_.

When you are done with your tests do not forget to deactivate the virtual
environment:

.. code::

  (venv) $ deactivate


