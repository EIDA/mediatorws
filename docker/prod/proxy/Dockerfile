# Loopback proxy configuration
# -----------------------------------------------------------------------------
# Build Container:
# docker build -t eida-federator-proxy:1.0 .
#
# Run Container:
# docker run [-d] [--rm] [--name eida-federator-proxy] -p 8090:80 \
#   eida-federator-proxy:1.0
#
# Modify running container:
# docker exec -it eida-federator-proxy /bin/bash

# Base image
FROM phusion/baseimage:0.11

# Add label metadata
LABEL maintainer="Daniel Armbruster"
LABEL email="daniel.armbruster@sed.ethz.ch"

CMD ["/sbin/my_init"]

# System dependencies
RUN apt-get update && apt-get install -y apache2

# Copy Apache configuration
COPY httpd.conf /etc/apache2/sites-available/

# Enable vhosts
RUN a2dissite 000-default.conf
RUN a2ensite httpd.conf

# Enable required modules 
RUN a2enmod cache_disk headers proxy_http

# Add the apache2 service
RUN mkdir /etc/service/apache2 && \
          echo "#!/bin/sh\nexec apachectl -D FOREGROUND" > /etc/service/apache2/run && \
          chmod +x /etc/service/apache2/run

# Expose Apache2 default port
EXPOSE 80

# Clean up (baseimage recommended)
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
