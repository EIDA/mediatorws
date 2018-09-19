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

Run the Test WSGI servers
=========================

The webservices are implemented using the `Flask <http://flask.pocoo.org/>`_
framework.

The examples bellow use the built-in Flask server, which is not recommended to
use in production. In production environments the usage of a WSGI server should
be preferred. An exemplary setup with *mod_wsgi* and Apache2 is described in
the section `Deploying to a webserver`_. Alternatively use Gunicorn or uWSGI.

Federator server
----------------

To launch a local test WSGI server (**NOT** for production environments) enter:

.. code::

  (venv) $ eida-federator --start-local --tmpdir='/path/to/tmp'

For further configuration options invoke

.. code::

  (venv) $ eida-federator -h

The service currently writes temporary files to the :code:`tmpdir`, so this directory will
fill up. It is recommended to purge this directory regularly, e.g., using a
tool like `tmpreaper`.

StationLite server
------------------

To launch a local test WSGI server (**NOT** for production environments) enter:

.. code::

  (venv) $ eida-stationlite --start-local URL

`URL` is a database url as described at the `SQLAlchemy documentation
<http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>`_.
For further configuration options invoke

.. code::

  (venv) $ eida-stationlite -h

Mediator server
---------------

.. note::

  The EIDA Mediator webservice currently still does not provide an installation
  routine. However, a test server can be started as described bellow. Note,
  that you have to install all dependencies required manually.

Add the repository directory to your PYTHONPATH. Then, the server can be
started as

.. code::

  $ python -m eidangservices.mediator.server --port=5001 --tmpdir='/path/to/tmp'

The server writes temporary files to the tmpdir, so this directory will fill up.
It is recommended to purge this directory regularly, e.g., using a tool like
`tmpreaper`.


Deploying to a webserver
========================

.. note::

  Currently the deployment to a webserver only is setup for the EIDA Federator
  and StationLite webservices.

This HOWTO describes the deployment by means of *mod_wsgi* for the Apache2
webserver. Make sure, that Apache2 is installed. 

It is also assumed, that you install the EIDA NG webservices to 

.. code::

  $ export PATH_INSTALLATION_DIRECTORY=/var/www

Next, proceed as described for a *test* installation from the `Download`_
section on.

When you installed the webservices successfully return to this point.

.. note::

  In case you would like to install the webservices to a different location
  i.e. :code:`PATH_INSTALLATION_DIRECTORY=/path/to/my/eida/webservices` make
  sure to adjust the configuration in the files
  :code:`$PATH_INSTALLATION_DIRECTORY/mediatorws/apache2/YOUR_SERVICE.{conf,wsgi}` manually.

Install *mod_wsgi*
------------------

If you don't have `mod_wsgi <https://modwsgi.readthedocs.io/en/develop/>`_
installed yet you have to either install it using a package manager or compile
it yourself.

If you are using Ubuntu/Debian you can apt-get it and activate it as follows:

.. code::

  # apt-get install libapache2-mod-wsgi
  # service apache2 restart

Setup a virtual host
--------------------

Exemplary Apache2 virtual host configuration files are found at
:code:`PATH_INSTALLATION_DIRECTORY/mediatorws/apache2/*.conf`. Adjust a copy of
those files according to your needs. Assuming you have an Ubuntu Apache2
configuration, copy the adjusted files to :code:`/etc/apache2/sites-available/`.
Then, enable the virtual hosts and reload the apache2 configuration:

.. code::

  # export MY_EIDA_SERVICES="list of EIDA NG services"
  # cd /etc/apache2/sites-available
  # for s in $MY_EIDA_SERVICES; do a2ensite $s.config; done
  # service apache2 reload

.. note::

  When using domain names in virtual host configuration files make sure to
  add an entry for those domain names in :code:`/etc/hosts`.
  
Configure the webservice 
------------------------

Besides of passing configuration options on the commandline, the EIDA NG
webservices also may be configured by means of an INI configuration file. You
find a documented version of this file under
:code:`$PATH_INSTALLATION_DIRECTORY/mediatorws/config/eidangws_config`.

The default location of the configuration file is
:code:`/var/www/mediatorws/config/eidangws_config`. To load this file from your
custom location comment out the lines 

.. code:: python

  #import eidangservices.settings as settings
  #settings.PATH_EIDANGWS_CONF = '/path/to/your/custom/eidangws_config'

in your :code:`*.wsgi` file. Also, adjust the path. Finally, restart the
Apache2 server.

Stationlite configuration
^^^^^^^^^^^^^^^^^^^^^^^^^

In order to run the *stationlite* webservice in production mode within
your `eidangws_config` you must provide a valid `URL` to a *stationlite* DB.

Within the configuration section `CONFIG_STATIONLITE` in your `eidangws_config`
comment out the line 

.. code::

  # db_url = sqlite:////abs/path/to/stationlite.db

and set the path accordingly. Restart Apache and check your `error.log`.


