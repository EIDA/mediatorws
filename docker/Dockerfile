# Dockerizing EIDA NG Mediator, Federator and StationLite images
# Following the instructions from:
#
# https://github.com/EIDA/mediatorws
#
# Build Container:
# docker build -t eida-federator:1.0 .
#
# Run Container:
# docker run [-d] [--rm] [--name eida-federator] -p 8080:80 eidang_federator:1.0
#
# Modify running container:
# docker exec -it eida-federator /bin/bash

# Base image
FROM phusion/baseimage:latest

# Add label metadata
LABEL maintainer="Massimo Fares"
LABEL email="massimo.fares@ingv.it"

CMD ["/sbin/my_init"]

# System dependencies
RUN apt-get update && apt-get install -y libxml2-dev \
                                         libxslt-dev \
                                         python-dev \
                                         git \
                                         build-essential \
                                         python-setuptools \
                                         zlib* \
                                         python-pip \
                                         pkg-config \
                                         libpng-dev \
                                         libfreetype6-dev \
                                         libblas-dev \
                                         liblapack-dev \
                                         apache2 \
                                         libapache2-mod-wsgi

# Update pip
RUN pip install --upgrade pip

# Install the Python dependencies
RUN pip install numpy obspy

# Get the source from GitHub:master
RUN git clone https://github.com/EIDA/mediatorws.git /var/www/mediatorws

# Install the services
WORKDIR /var/www/mediatorws
RUN make install

# Copy Apache configuration configuration
COPY federator.conf /etc/apache2/sites-available/

# Copy the WSGI configuration scripts
COPY *.wsgi /var/www/mediatorws/apache2/

# The default configuration
COPY eidangws_config /var/www/mediatorws/config/

# Copy an empty stationlite database
RUN cp db/stationlite.db.empty db/stationlite.db

# Give read permissions
RUN chmod +r /var/www/mediatorws/config/eidangws_config
RUN chmod +r /var/www/mediatorws/apache2/*.wsgi

# Enable the supplied WSGI modules
RUN a2ensite federator.conf

# Add the apache2 service
RUN mkdir /etc/service/apache2
COPY apache2.sh /etc/service/apache2/run
RUN chmod +x /etc/service/apache2/run

# Add the harvesting cronjob (once per day)
RUN (crontab -l ; echo "0 1 * * * python /var/www/mediatorws/eidangservices/stationlite/harvest/harvest.py sqlite:////var/www/mediatorws/db/stationlite.db") | crontab

RUN mkdir /var/www/mediatorws/log && chown www-data: /var/www/mediatorws/log

COPY logging.conf /var/www/mediatorws/config/logging.conf

# Expose Apache2 default port
EXPOSE 80

# Clean up
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
