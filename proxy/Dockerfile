# Base image
FROM phusion/baseimage:latest

# Add label metadata
LABEL maintainer="Mathijs Koymans"
LABEL email="koymans@knmi.nl"

CMD ["/sbin/my_init"]

# System dependencies
RUN apt-get update && apt-get install -y libxml2-dev \
                                         libxslt-dev \
                                         python3-dev \
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
                                         libapache2-mod-wsgi-py3

# Copy Apache configuration configuration
COPY *.conf /etc/apache2/sites-available/

# Enable the supplied WSGI modules
RUN a2ensite noa.conf

# Enable required modules 
RUN a2enmod file_cache proxy headers

# Add the apache2 service
RUN mkdir /etc/service/apache2 && \
          echo "#!/bin/sh\nexec apachectl -D FOREGROUND" > /etc/service/apache2/run && \
          chmod +x /etc/service/apache2/run

# Expose Apache2 default port
EXPOSE 80

# Clean up (baseimage recommended)
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
