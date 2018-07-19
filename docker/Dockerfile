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
FROM ubuntu:16.04 

# Add label metadata
LABEL maintainer="Massimo Fares"
LABEL email="massimo.fares@ingv.it"

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
                                         libpng12-dev \
                                         libfreetype6-dev \
                                         libblas-dev \
                                         liblapack-dev \
                                         apache2 \
                                         libapache2-mod-wsgi

# Install the Python dependencies
RUN pip install numpy obspy virtualenv

# Get the source from GitHub:master
RUN git clone https://github.com/EIDA/mediatorws.git /var/www/mediatorws

# Create virtual environments for federator/stationlite
RUN virtualenv /var/www/federator/venv && virtualenv /var/www/stationlite/venv

# Install the services
WORKDIR /var/www/mediatorws
RUN make ls && make install

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

# Expose Apache2 default port
EXPOSE 80

# Run Apache in the foreground
CMD ["apachectl", "-D", "FOREGROUND"]
