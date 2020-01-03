# Dockerizing EIDA NG Federator and StationLite images
# Following the instructions from:
#
# https://github.com/EIDA/mediatorws
#
# Build Container:
# docker build -t eida-federator:1.0 .
#
# Run Container:
# docker run [-d] [--rm] [--name eida-federator] -p 8080:80 eida-federator:1.0
#
# Modify running container:
# docker exec -it eida-federator /bin/bash

# Base image
FROM phusion/baseimage:0.11

# Add label metadata
LABEL maintainer="Mathijs Koymans"
LABEL email="koymans@knmi.nl"

CMD ["/sbin/my_init"]

# System dependencies
RUN apt-get update && apt-get install -y libxml2-dev \
                                         libxslt-dev \
                                         python3-dev \
                                         python3-setuptools \
                                         python3-pip \
                                         git \
                                         build-essential \
                                         zlib* \
                                         pkg-config \
                                         libpq-dev \
                                         libpng-dev \
                                         libfreetype6-dev \
                                         libblas-dev \
                                         liblapack-dev \
                                         apache2 \
                                         libapache2-mod-wsgi-py3

# Update pip
RUN pip3 install --upgrade pip

# Install Python packages
RUN pip3 install virtualenv

# Get the source from GitHub:master
RUN git clone https://github.com/EIDA/mediatorws.git /var/www/mediatorws

# Install the services
WORKDIR /var/www/mediatorws

# Create the virtual environments
RUN mkdir /var/www/federator && cd /var/www/federator && \
    virtualenv -p $(which python3.6) venv3 && \
    /bin/bash -c "source /var/www/federator/venv3/bin/activate && \
    make -C /var/www/mediatorws install SERVICES=federator && deactivate"

RUN mkdir /var/www/stationlite && cd /var/www/stationlite && \
    virtualenv -p $(which python3.6) venv3 && \
    /bin/bash -c "source /var/www/stationlite/venv3/bin/activate && \
    pip install numpy psycopg2 && \
    make -C /var/www/mediatorws install SERVICES=stationlite && deactivate"

# Copy Apache configuration configuration
COPY federator.conf /etc/apache2/sites-available/

# Copy the WSGI configuration scripts
COPY *.wsgi /var/www/mediatorws/apache2/

# The service and harvesting configuration
COPY *_config /var/www/mediatorws/config/

# Give read permissions
RUN chmod +r /var/www/mediatorws/config/eidangws_config /var/www/mediatorws/apache2/*.wsgi

# Enable the supplied WSGI modules
RUN a2dissite 000-default.conf
RUN a2ensite federator.conf

# Add the apache2 service
RUN mkdir /etc/service/apache2 && \
	echo "#!/bin/sh\nexec apachectl -D FOREGROUND" > /etc/service/apache2/run && \
	chmod +x /etc/service/apache2/run

# Add the harvesting cronjobs (once per day)
COPY .env /var/www/mediatorws/docker/prod/federator/cron-env
RUN sed -e 's/^/export /' -i /var/www/mediatorws/docker/prod/federator/cron-env
RUN (crontab -l ; echo "0 1 * * * source /var/www/mediatorws/docker/prod/federator/cron-env; /var/www/stationlite/venv3/bin/eida-stationlite-harvest --config /var/www/mediatorws/config/harvest_other_config") | crontab
RUN (crontab -l ; echo "0 4 * * * source /var/www/mediatorws/docker/prod/federator/cron-env; /var/www/stationlite/venv3/bin/eida-stationlite-harvest --config /var/www/mediatorws/config/harvest_station_config") | crontab

RUN mkdir -p /var/www/mediatorws/log && chown www-data:www-data /var/www/mediatorws/log
RUN mkdir -p /var/tmp/ && chown www-data:www-data /var/tmp/

# Add the logging configuration
COPY fed-logging.conf /var/www/mediatorws/config/fed-logging.conf
COPY stl-logging.conf /var/www/mediatorws/config/stl-logging.conf
COPY harvest-logging.conf /var/www/mediatorws/config/harvest-logging.conf

# Expose Apache2 default port
EXPOSE 80

# Clean up (baseimage recommended)
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
