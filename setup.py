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


def get_version(filename):
    from re import findall
    with open(filename) as f:
        metadata = dict(findall("__([a-z]+)__ = '([^']+)'", f.read()))
    return metadata['version']


_name = 'eidangservices'
_version = '0.9.1'
_author = "Fabian Euchner, Daniel Armbruster"
_author_email = "fabian.euchner@sed.ethz.ch, daniel.armbruster@sed.ethz.ch"
_description = ("EIDA NG Mediator/Federator webservices")
_entry_points = {
    'console_scripts': [
        'eida-federator = eidangservices.federator.server.app:main',
    ]
}
_includes = ('*')
_deps = [
        'fasteners>=0.14.1',
        'Flask>=0.12.2',
        'Flask-RESTful>=0.3.6',
        # TODO(damb): Seems not to work for Python 2.7
        #'mock:python_version<"3.3"',
        'future>=0.16.0',
        'marshmallow>=3.0.0b4',
        'webargs>=1.8.1',
        ]

if sys.version_info[:2] < (3, 3):
    _deps.append('mock')


subsys = sys.argv[1]
if 'federator' == subsys:
    # configure the federator setup
    sys.argv.pop(1)

    _name = 'federator'
    _version = get_version('eidangservices/federator/__init__.py')
    _author = "Daniel Armbruster, Fabian Euchner"
    _author_email = ("daniel.armbruster@sed.ethz.ch, " +
        "fabian.euchner@sed.ethz.ch")
    _description = ("EIDA NG Federator webservice")
    _entry_points = {
        'console_scripts': [
            'eida-federator = eidangservices.federator.server.app:main',
        ]
    }
    _includes = ('eidangservices',
            '*.federator', 'federator.*', '*.federator.*')
    _deps = [
            'fasteners>=0.14.1',
            'Flask>=0.12.2',
            'Flask-RESTful>=0.3.6',
            # TODO(damb): Seems not to work for Python 2.7
            #'mock:python_version<"3.3"',
            'future>=0.16.0',
            'marshmallow>=3.0.0b4',
            'webargs>=1.8.1',
            ]
    if sys.version_info[:2] < (3, 3):
        _deps.append('mock')


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
    version = _version,
    author = _author,
    author_email = _author_email,
    description = _description,
    long_description='',
    license = "",
    keywords = "seismology waveforms federation mediation eida service",
    url = "https://github.com/EIDA/mediatorws",
    platforms=['Linux',],
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
    packages=find_packages(include=_includes),
    include_package_data=True,
    install_requires = _deps,
    entry_points = _entry_points,
    zip_safe=False
)

# ---- END OF <setup.py> ----
