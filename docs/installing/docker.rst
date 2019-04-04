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
change into the :code:`docker/` directory and change the configuration.

**Postgres**:

The docker distribution uses stationlite with postgres. You are required to set
up and initial empty postgres database that can be used by stationlite. Make
sure to pick a proper username and password and write these down. A volume
must be mounted where the postgres data will be stored with the -v flag. The
volume must match what is configured in the *docker-compose.yml* file.

.. code::

  $ docker run --rm -e POSTGRES_USER=user \
                    -e POSTGRES_PASSWORD=pass \
                    -e POSTGRES_DB=stationlite \
                    -v /var/db/psql:/var/lib/postgresql/data \
                    postgres:11


Follow up by configuring the following parameters in docker/eidangws_config
with your postgres parameters. The host localhost must be replaced with the name
of the postgres container (e.g. docker_psql_1).

.. code::

  $ cd docker
  db_url = postgresql://user:pass@localhost:5432/stationlite
  db_engine = postgresql://user:pass@localhost:5432/stationlite

Other important configuration parameters are for logging. Once the configuration
is complete continue by building the image:

.. code::

  $ cd docker && docker build -t eida-federator:1.0 .

**Deployment**:

The container should be run using the provided :code:`docker-compose.yml`
configuration file.

.. code::

  $ docker-compose up -d

When deploying for the first time you are required to initialize the database for
*stationlite*. This will create the database schema.

.. code::

  $ docker exec <container_name> \
      /var/www/stationlite/venv3/bin/eida-stationlite-db-init \
      postgresql://user:pass@localhost:5432/stationlite

and the harvesting:

.. code::

  $ docker exec <container_name> \
      /var/www/stationlite/venv3/bin/eida-stationlite-harvest \
      postgresql://user:pass@localhost:5432/stationlite

The initial harvesting may take some time. In the future it will be run by a daily cronjob.

When the containers are running the services are now available under
:code:`http://localhost:8080`.
