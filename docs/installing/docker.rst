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

**Building**:

To construct a Docker image with the appropriate configuration it is recommended to build your image from a Dockerfile. Change in to the docker directory and build the image

.. code::

  $ cd docker
  $ docker build -t eida-federator:1.0 .

  # Create persistent directories (make sure there is plenty of disk space)
  # These will need to be configured in docker-compose.yml (see below)
  $ mkdir -p <archive>/db
  $ mkdir -p <archive>/var/log
  $ mkdir -p <archive>/var/tmp

  # Add a persistent file for stationlite sqlite to the mounted volume
  $ cp ../db/stationlite.db.empty <archive>/db/stationlite.db

**Running**:

The container can be run using the provided `docker-compose.yml` configuration. Make sure that the appropriate data volumes are mounted to make sure the stationlite database, log files, and temporary data files are persistent.

.. code::

  $ docker-compose up

  # When running for the first time we will kickstart the harvesting for stationlite
  # This will automatically run in a daily cronjob
  $ docker exec <container_name> python /var/www/mediatorws/eidangservices/stationlite/harvest/harvest.py sqlite:////var/www/mediatorws/db/stationlite.db

After that the Federator should work.
