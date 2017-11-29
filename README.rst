**************************************
EIDA NG Mediator/Federator webservices
**************************************

This repository is intended to contain the source code for two of the web
services of EIDA NG: (i) the *federator*, and (ii) the *mediator*.

*Federator*: Federate `fdsnws-station`, `fdsnws-dataselect`, and 
`eidaws-wfcatalog`requests across all EIDA nodes. This means, a user can issue 
a request against a federator endpoint without having to know where the data is 
hosted. In order to discover the information location, the `eidaws-routing` web 
service is used.

*Mediator*: This service allows queries across different web service domains, 
e.g., `fdsnws-station` and `fdsnws-dataselect`. Example: Retrieve waveform data
for all stations within a lat-lon box.

Currently, we provide an alpha version of the federator service for
`fdsnws-station`, `fdsnws-dataselect` and `eidaws-wfcatalog`. The federator is
largely based on the **fdsnws_fetch** tool by GFZ (with only small
modifications).

Installation
============

.. note::

  This installation method currently only is prepared for the EIDA Federator
  webservice. 

This is the recommended installation method of the EIDA NG webservices for
simple test purposes. The installation is performed by means of the
`virtualenv <https://pypi.python.org/pypi/virtualenv>`_ package.

First of all, choose an installation directory:

.. code::

  PATH_INSTALLATION_DIRECTORY=$HOME/work

Download the EIDA NG webservices
--------------------------------

From the `EIDA GitHub <https://github.com/EIDA/mediatorws>`_ download a copy of
the *mediatorws* source code:

.. code::

  $ cd $PATH_INSTALLATION_DIRECTORY
  $ git clone https://github.com/EIDA/mediatorws


Installing *virtualenv*
-----------------------

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

Finally activate the virtual environment:

.. code::

  $ . $PATH_INSTALLATION_DIRECTORY/mediatorws/venv/bin/activate

.. note::

  When using a Python virtual environment with *mod_wsgi*, it is very important
  that it has been created using the same Python installation that *mod_wsgi*
  was originally compiled for. It is **not** possible to use a Python virtual
  environment to force *mod_wsgi* to use a different Python version, or even a
  different Python installation.

Install EIDA NG webservices
---------------------------

EIDA NG webservices provide installation routines. After activating the virtual
environment execute:

.. code::

  $ make install

This command will install all EIDA NG webservices available. To install a
specific service (e.g. the federator) from the package enter:

.. code::

  $ make install SERVICE=federator

Besides of the federator webservice the command will resolve and install all
dependencies necessary.

Finally test your federator installation with

.. code::

  $ eida-federator -V

When you are done with your tests do not forget to deactivate the virtual
environment:

.. code::

  $ deactivate


Deploying to a webserver
========================

.. note::

  Currently the deployment to a webserver only is setup for the EIDA Federator
  webservice.

This HOWTO describes the deployment by means of *mod_wsgi* for the Apache2
Webserver. Make sure, that Apache2 is installed. 

It is also assumed, that you install the EIDA NG webservices to 

.. code::

  PATH_INSTALLATION_DIRECTORY=/var/www

Then, proceed as described for a *test* installation from the `Download the
EIDA NG webservices`_ section on. When
you installed the webservices successfully return to this point.

Install *mod_wsgi*
------------------

If you don’t have *mod_wsgi* installed yet you have to either install it using
a package manager or compile it yourself.

If you are using Ubuntu/Debian you can apt-get it and activate it as follows:

.. code::

  # apt-get install libapache2-mod-wsgi
  # service apache2 restart

Setup a virtual host
--------------------

Exemplary Apache2 virtual host configuration files are found at
:code:`PATH_INSTALLATION_DIRECTORY/mediatorws/apache2/`. Adjust a copy of those
files according to your needs. Assuming you have an Ubuntu Apache2
configuration, copy the adjusted files to :code:`/etc/apache2/sites-available/`.
Then, enable the virtual hosts and reload the apache2 configuration:

.. code::

  # a2ensite federator.config
  # service apache2 reload

.. note::

  When using a domain name in the virtual host configuration file make sure to
  add an entry for this domain name in :code:`/etc/hosts`.
  
Configure the webservice 
------------------------

You may configure the EIDA NG webservices (currently Federator only) by means
of a INI configuration file. The default location of the configuration file is
`/var/www/mediatorws/config/eidangws_config`. To load this file from a custom
location comment out the lines 

.. code:: python

  #import eidangservices.settings as settings
  #settings.PATH_EIDANGWS_CONF = '/path/to/your/custom/eidangws_conf'

in your *wsgi* file. Also, adjust the path. Restart the Apache2 server.

.. todo:
  
  (damb): To be tested.

Federator server
================

The server is implemented using the `Flask <http://flask.pocoo.org/>`_
framework.

To launch a local test WSGI server (**NOT** for production environments) enter:

.. code::

  $ eida-federator --start-local

For further configuration options visit

.. code::

  $ eida-federator -h

The server writes temporary files to the :code:`tmpdir`, so this directory will
fill up. It is recommended to purge this directory regularly, e.g., using a
tool like tmpreaper.

In production environments, the usage of a WSGI server should be preferred. The
setup with *mod_wsgi* and Apache2 is described in the section `Deploying to a
webserver`_.

Mediator server
===============

.. note::

  The EIDA Mediator server currently still does not provide an installation
  routine. However, a test server can be started as described bellow.

The server is implemented using the Flask framework, in particular, they use 
the flask-RESTful package. Add the repository directory to your PYTHONPATH.
Then, the server can be started as

.. code::

  $ python -m eidangservices.mediator.server --port=5001 --tmpdir='/path/to/tmp'

The server writes temporary files to the tmpdir, so this directory will fill up.
It is recommended to purge this directory regularly, e.g., using a tool like
tmpreaper.

To expose the service to port 80, a reverse proxy like nginx should be used. 

This example uses the built-in Flask server, which is not recommended to use in
production. In production environments, usage of a WSGI server like Gunicorn or
uWSGI should be preferred.

Missing features and limitations
================================

* The **/queryauth** route of the `fdsnws-dataselect` service is not yet
  implemented
* Error message texts are JSON, not plain text


