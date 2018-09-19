Deploying the EIDA NG webservice Docker container
=================================================

.. note::

  Currently only *federator* and *stationlite*.

A basic knowledge about `Docker <https://docs.docker.com/engine/>`__ and how
this kind of application containers work is required. For more information
about operating system support (which includes Linux, macOS and specific
versions of Windows) and on how to install Docker, please refer to the official
`Docker website <https://www.docker.com/products/docker>`_.

Images are hosted on `Docker Hub <https://hub.docker.com/r/damb/mediatorws/>`_.

**Features provided**:

* based on `baseimage <https://hub.docker.com/r/phusion/baseimage/>`_
* :code:`apache2` + `mod_wsgi <https://github.com/GrahamDumpleton/mod_wsgi>`_ for Python 3
* *federator* and *stationlite* are set up separately i.e. each
  service is installed into its own virtual environment
* services use Python3
* user :code:`eida:www` runs the :code:`mod_wsgi` deamon processes
* *stationlite* harvesting via :code:`cron`

**Available tags**:

.. code::

  $ docker pull damb/mediatorws:latest

**Deployment**:

.. code::

  $ docker run --name <container_name> -d -p 8080:80 damb/mediatorws:latest

Then the services are available under :code:`http://localhost:8080`. In order to have
a working *stationlite* service invoke

.. code::

  $ docker exec --user eida <container_name> \
  /var/www/stationlite/venv3/bin/eida-stationlite-harvest sqlite:////var/www/stationlite/db/stationlite.db

Harvesting may take some time.
