Deploying the EIDA NG Federator as a Docker container
=====================================================

.. note::

  Currently only *federator* and *stationlite*.

A basic knowledge about `Docker <https://docs.docker.com/engine/>`__ and how
this kind of application containers work is required. For more information
about operating system support (which includes Linux, macOS and specific
versions of Windows) and on how to install Docker, please refer to the official
`Docker website <https://www.docker.com/products/docker>`_.

**Features provided**:

* based on `baseimage <https://hub.docker.com/r/phusion/baseimage/>`_
* :code:`apache2` + `mod_wsgi <https://github.com/GrahamDumpleton/mod_wsgi>`_ for
  for Python 3
* *federator* and *stationlite* are set up separately i.e. each
  service is installed into its own virtual environment
* services use Python3
* *stationlite* harvesting via :code:`cron`
* logging (file based)

**Building**:

To construct a Docker image with the appropriate configuration it is
recommended to build your image from a Dockerfile. After cloning the repository
change into the :code:`docker/` directory and build the image:

.. code::

  $ cd docker && docker build -t eida-federator:1.0 .

**Deployment**:

The container should be run using the provided :code:`docker-compose.yml`
configuration file.

.. code::

  $ docker-compose up -d

When deploying for the first time you are required to kickstart the harvesting for
*stationlite*:

.. code::

  $ docker exec <container_name> \
      /var/www/stationlite/venv3/bin/eida-stationlite-harvest \
      sqlite:////var/www/mediatorws/db/stationlite.db

The initial harvesting may take some time. In the future it will be run by a daily cronjob.
The services are now available under :code:`http://localhost:8080`.
