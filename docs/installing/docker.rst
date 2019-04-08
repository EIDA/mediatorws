Deploying the EIDA NG Federator as a Docker container
=====================================================

.. note::

  Currently includes *federator* and *stationlite*.

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
* *stationlite* harvesting via :code:`cron` powered by `PostgreSQL
  <https://www.postgresql.org/>`_
* logging (file based)

**Introduction**:

To construct a Docker image with the appropriate configuration it is
recommended to build your image from a Dockerfile. After cloning the repository
change into the :code:`docker/` directory and modify the configuration.

.. code::

  $ cd docker

**Configuration**:

Before building and running the container adjust the variables defined within
:code:`.env` configuration file according to your needs. Make sure to pick a
proper username and password for the internally used PostgreSQL database and
write these down for later.

**Building**:

Once you environment variables are configured you are ready to build the
container image.

.. code::

  $ docker build -t eida-federator:1.0 .

**Compose Configuration**:

In case you want to manage your own volumes now is the time. The configuration
provided relies on named docker volumes.

**Deployment**:

The container should be run using the provided :code:`docker-compose.yml`
configuration file.

.. code::

  $ docker-compose up -d

When deploying for the first time you are required to initialize the database
for *stationlite*. This will create the database schema.

.. code::

  $ docker exec <container_name> \
      /var/www/stationlite/venv3/bin/eida-stationlite-db-init \
      --logging-conf /var/www/mediatorws/config/logging.conf \
      postgresql://user:pass@localhost:5432/stationlite

and the harvesting:

.. code::

  $ docker exec <container_name> \
      /var/www/stationlite/venv3/bin/eida-stationlite-harvest \
      postgresql://user:pass@localhost:5432/stationlite

The initial harvesting may take some time. In the future it will be run by a
daily cronjob.

When the containers are running the services are now available under
:code:`http://localhost:8080`.
