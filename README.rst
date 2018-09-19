.. |BuildStatus| image:: https://jenkins.ethz.ch/buildStatus/icon?job=mediatorws
                  :alt: Build Status
.. _BuildStatus: https://jenkins.ethz.ch/job/mediatorws

**************************************
EIDA NG Mediator/Federator webservices
**************************************

|BuildStatus|_ (py27, py34, py35, py36)

This repository is intended to contain the source code for three of the web
services of EIDA NG: (i) the *federator*, (ii) *stationlite* and (iii) the
*mediator*.

**Federator**: Federate *fdsnws-station*, *fdsnws-dataselect*, and 
*eidaws-wfcatalog* requests across all EIDA nodes. This means, a user can issue 
a request against a *federator* endpoint without having to know where the data
is hosted. In order to discover the information location, either the
*eidaws-routing* or the *eidaws-stationlite* web service is used.

**StationLite**: A lightweight *fdsnws-station* web service providing routing
information. The stream epoch information is returned fully resolved (Stream
epochs do not contain wildcard characters anymore.). The information location
is harvested making use of *eidaws-routing* configuration files and
*fdsnws-station*.

**Mediator**: This service allows queries across different web service domains, 
e.g., *fdsnws-station* and *fdsnws-dataselect*. Example: Retrieve waveform data
for all stations within a lat-lon box.

Currently, we provide an alpha version of the *federator* service for
*fdsnws-station*, *fdsnws-dataselect* and *eidaws-wfcatalog*.

Besides an alpha version of the *stationlite* service is implemented.


Content
=======

* `Installation`_
* `Run the Test WSGI servers`_
* `StationLite harvesting`_
* `Logging (application level)`_
* `Missing features and limitations`_


Installation
============

* `Development
  <https://github.com/EIDA/mediatorws/tree/master/docs/installing/development.rst>`_
* `Docker <https://github.com/EIDA/mediatorws/tree/master/docs/docker.rst>`_


Run the Test WSGI servers
=========================

The examples bellow use the built-in `Flask <http://flask.pocoo.org/>`_ server,
which is not recommended to use in production. In production environments the
usage of a WSGI server should be preferred. An exemplary setup with *mod_wsgi*
and Apache2 is described in the section `Deploying to a webserver
<https://github.com/EIDA/mediatorws/tree/master/docs/installing/development.rst#Deploying
to a webserver>`_. Alternatively use Gunicorn or uWSGI.

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

StationLite harvesting
======================

The *stationlite* webservice data is stored in a database which periodically
must be harvested. This is done with `eida-stationlite-harvest`. By means of
the *eidaws-routing* configuration files and the *fdsnws-station* webservice
`eida-stationlite-harvest` collects and updates the database. Information on
how to use `eida-stationlite-harvest` is available with

.. code::

  (venv) $ eida-stationlite-harvest -h

In addition the software suite contains an empty exemplary preconfigured
*SQLite* database (`db/stationlite.db.empty`) which must be filled initially
after installing the *stationlite* webservice. I.e.

.. code::

  (venv) $ cd $PATH_INSTALLATION_DIRECTORY/mediatorws/
  (venv) $ cp -v db/stationlite.db.empty db/stationlite.db
  (venv) $ eida-stationlite-harvest sqlite:///$(pwd)/db/stationlite.db

Note, that harvesting may take some time until completed.


Logging (application level)
===========================

.. note::

  EIDA Federator and StationLite webservices only.

For debugging purposes EIDA NG webservices also provide logging facilities.
Simply configure your webservice with a logging configuration file. Use the INI
`logging configuration file format
<https://docs.python.org/library/logging.config.html#configuration-file-format>`_.
In case initialization failed a fallback `SysLogHandler
<https://docs.python.org/library/logging.handlers.html#sysloghandler>`_ is
set up:

.. code:: python

  fallback_handler = logging.handlers.SysLogHandler('/dev/log',
                                                    'local0')
  fallback_handler.setLevel(logging.WARN)
  fallback_formatter = logging.Formatter(
      fmt=("<XXX> %(asctime)s %(levelname)s %(name)s %(process)d "
           "%(filename)s:%(lineno)d - %(message)s"),
      datefmt="%Y-%m-%dT%H:%M:%S%z")
  fallback_handler.setFormatter(fallback_formatter)

An exemplary logging configuration using a SysLogHandler is located at
:code:`$PATH_INSTALLATION_DIRECTORY/mediatorws/config/syslog.conf`. At :code:`$PATH_INSTALLATION_DIRECTORY/mediatorws/config/logging.config` a
`StreamHandler
<https://docs.python.org/library/logging.handlers.html#streamhandler>`_ is
configured.


.. note::

  1. In order to keep the WSGI application portable you should avoid setting up
  a logger writing to :code:`sys.stdout`. See also:
  http://modwsgi.readthedocs.io/en/develop/user-guides/debugging-techniques.html

  2. When using an EIDA NG multithreaded webservice together with a *mod_wsgi*
  configuration processes `logging to a single file 
  <https://docs.python.org/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes>`_
  is not supported. Instead initialize your logger with a handler which
  guarantees log messages to be serialized (e.g. `SysLogHandler`_,
  `SocketHandler
  <https://docs.python.org/library/logging.handlers.html#sockethandler>`_).


Missing features and limitations
================================

* The **/queryauth** route of the `fdsnws-dataselect` service is not yet
  implemented
* *stationlite* currently implements the *eidaws-routing* interface only partly
  (e.g. `format={post,get}`)
* For issues also visit https://github.com/EIDA/mediatorws/issues.
