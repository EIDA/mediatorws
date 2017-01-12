EIDA NG Mediator/Federator webservices
======================================

This repository is intended to contain the source code for two of the web
services of EIDA NG: (i) the federator, and (ii) the mediator.

Federator: Federate fdsnws-station, fdsnws-dataselect, and eidaws-WFCatalog
requests across all EIDA nodes. This means, a user can issue a request against
a federator endpoint without having to know where the data is hosted. In order 
to discover the information location, the eidaws-routing web service is used.

Mediator: This service allows queries across different web service domains, 
e.g., fdsnws-station and fdsnws-dataselect. Example: Retrieve waveform data
for all stations within a lat-lon box.

Currently, we provide an alpha version of the federator service for
fdsnws-station and fdsnws-dataselect. The federator is largely based on the 
fdsnws_fetch tool by GFZ (with only small modifications).


Missing features and limitations
--------------------------------

* only /query method is implemented (dataselect /queryauth is not implemented)
* error message texts are JSON, not plain text


Federator server
----------------

The server is implemented using the Flask framework, in particular, it uses 
the flask-RESTful package. Add the repository directory to your PYTHONPATH.
Then, the server can be started as

````
python -m federator.server --port=5000 --routing='gfz' --tmpdir='/path/to/tmp'
````

For the routing parameter, one of these acronyms can be used:
gfz (default), odc, eth, ingv, bgr, lmu, ipgp, koeri, noa

The server writes temporary files to the tmpdir, so this directory will fill up.
It is recommended to purge this directory regularly, e.g., using a tool like
tmpreaper.

To expose the service to port 80, a reverse proxy like nginx should be used. 

This example uses the built-in Flask server, which is not recommended to use in
production. In production environments, usage of a WSGI server like Gunicorn or
uWSGI should be preferred.
