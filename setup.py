# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <setup.py>
# -----------------------------------------------------------------------------
#
# REVISION AND CHANGES
# 2017/11/26        V0.1    Daniel Armbruster
# =============================================================================
"""
setup.py for EIDA NG Mediator/Federator webservices
"""

import sys
from setuptools import setup, find_packages

if sys.version_info[:2] < (2, 7) or (3, 0) <= sys.version_info[:2] < (3, 4):
    raise RuntimeError("Python version 2.7 or >= 3.4 required.")



_name = 'eidangservices'
_author = "Fabian Euchner, Daniel Armbruster"
_author_email = "fabian.euchner@sed.ethz.ch, daniel.armbruster@sed.ethz.ch"
_description = ("EIDA NG Mediator/Federator webservices")
_includes = ('*')
_deps = [
        'fasteners>=0.14.1',
        'Flask>=0.12.2',
        'Flask-RESTful>=0.3.6',
        #'mock:python_version<"3.3"',
        'marshmallow>=3.0.0b4',
        'webargs>=1.8.1',
        ]


subsys = sys.argv[1]
if 'federator' == subsys:
    # configure the federator setup
    sys.argv.pop(1)

    _name = 'federator'
    _author = "Daniel Armbruster, Fabian Euchner"
    _author_email = ("daniel.armbruster@sed.ethz.ch, " +
        "fabian.euchner@sed.ethz.ch")
    _description = ("EIDA NG Federator webservice")
    _includes = ('eidangservices',
            '*.federator', 'federator.*', '*.federator.*')
    _deps = [
            'fasteners>=0.14.1',
            'Flask>=0.12.2',
            'Flask-RESTful>=0.3.6',
            #'mock:python_version<"3.3"',
            'marshmallow>=3.0.0b4',
            'webargs>=1.8.1',
            ]

elif 'stationlite' == subsys:
    sys.argv.pop(1)
    pass
elif 'mediator' == subsys:
    sys.argv.pop(1)
    pass
else:
    pass
    # build the entire mediatorws package


setup(
    name = _name,
    version = "0.9.1",
    author = _author,
    author_email = _author_email,
    description = _description,
    license = "",
    keywords = "seismology waveforms federation mediation eida service",
    url = "https://github.com/EIDA/mediatorws",
    platforms=['Linux',],
    packages=find_packages(include=_includes),
    long_description='',
    classifiers=[
          "Development Status :: 3 - Alpha",
          "Framework :: Flask",
          "Environment :: Web Environment",
          "Intended Audience :: Science/Research",
          "Operating System :: POSIX :: Linux",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Server",
          "Topic :: Scientific/Engineering",
    ],
    install_requires = _deps,
    zip_safe=False
)

# ---- END OF <setup.py> ----
