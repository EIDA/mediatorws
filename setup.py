# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <setup.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices.
#
# EIDA NG webservices are free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# EIDA NG webservices are distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# ----
#
# Copyright (c) Daniel Armbruster (ETH), Fabian Euchner (ETH)
#
# REVISION AND CHANGES
# 2017/11/26        V0.1    Daniel Armbruster
# =============================================================================
"""
setup.py for EIDA NG Mediator/Federator webservices
"""

import os
import sys
from copy import deepcopy
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
_author = "Fabian Euchner (ETH), Daniel Armbruster (ETH)"
_author_email = "fabian.euchner@sed.ethz.ch, daniel.armbruster@sed.ethz.ch"
_description = ("EIDA NG Mediator/Federator webservices")

_entry_points_federator = {
    'console_scripts': [
        'eida-federator = eidangservices.federator.server.app:main',
    ]}
_entry_points_stationlite = {
    'console_scripts': [
        'eida-stationlite = eidangservices.stationlite.server.app:main',
        ('eida-stationlite-harvest = '
         'eidangservices.stationlite.harvest.harvest:main'),
        ('eida-stationlite-db-init = '
         'eidangservices.stationlite.harvest.misc:db_init'),
    ]}
_entry_points = _entry_points_federator.copy()
_entry_points['console_scripts'].append(
    _entry_points_stationlite['console_scripts'])

_includes = ('*')
# XXX(damb): Take care for possible dependency conflicts.
_deps_all = [
    'Flask>=0.12.2',
    'Flask-RESTful>=0.3.6',
    # TODO(damb): Seems not to work for Python 2.7
    # 'mock:python_version<"3.3"',
    'future>=0.16.0',
    'intervaltree>=2.1',
    'lxml>=4.2.0',
    'marshmallow==3.0.0b11',
    'python-dateutil>=2.6.1',
    'requests>=2.18.4',
    'webargs==3.0.0', ]
_deps_federator = _deps_all + [
    'Flask-Cors>=3.0.7',
    'ijson>=2.3', ]
_deps_stationlite = _deps_all + [
    'fasteners>=0.14.1',
    'Flask-SQLAlchemy>=2.3.2',
    'obspy>=1.1.0',
    'SQLAlchemy>=1.2.0', ]
_deps = deepcopy(_deps_federator)
_deps.extend(_deps_stationlite)
_deps = list(set(_deps))

_test_deps = ['pytest']
if sys.version_info[:2] < (3, 3):
    _test_deps.append('mock')

_extras = {
    'test': _test_deps,
}

_test_suites = [os.path.join('eidangservices', 'utils', 'tests')]

# NOTE(damb): Since this setup.py provides multiple package creation/deployment
# we exclusively deploy additionaly files by means of the 'data_files'
# parameter
_data_files_all = [
    ('', ['COPYING',
          'Makefile']),
    ('config', ['config/logging.conf',
                'config/syslog.conf'])]
_data_files_federator = [
    ('config', ['config/eida-federator.conf.rsyslog']),
    ('apache2', ['apache2/federator.conf',
                 'apache2/federator.wsgi']),
    ('eidangservices/federator/share',
        ['eidangservices/federator/share/dataselect.wadl',
         'eidangservices/federator/share/station.wadl',
         'eidangservices/federator/share/wfcatalog.wadl'])]
_data_files_stationlite = [
    ('config', ['config/eida-stationlite.conf.rsyslog']),
    ('apache2', ['apache2/stationlite.conf',
                 'apache2/stationlite.wsgi']),
    ('eidangservices/stationlite/share',
        ['eidangservices/stationlite/share/routing.wadl']),
    ('db', ['db/stationlite.db.empty'])]

_data_files = _data_files_all + _data_files_federator + _data_files_stationlite
_data_files_federator += _data_files_all
_data_files_stationlite += _data_files_all

subsys = sys.argv[1]
if 'federator' == subsys:
    # configure the federator setup
    sys.argv.pop(1)

    _name = 'federator'
    _version = get_version('eidangservices/federator/__init__.py')
    _author = "Daniel Armbruster (ETH), Fabian Euchner (ETH)"
    _author_email = ("daniel.armbruster@sed.ethz.ch, " +
                     "fabian.euchner@sed.ethz.ch")
    _description = ("EIDA NG Federator webservice")
    _includes = ('eidangservices', 'eidangservices.utils',
                 'eidangservices.utils.tests',
                 '*.federator', 'federator.*', '*.federator.*')
    _entry_points = _entry_points_federator

    _deps = _deps_federator
    _data_files = _data_files_federator

    if sys.version_info[:2] < (3, 3):
        _deps.append('mock')

    _test_suites.append(os.path.join('eidangservices', 'federator', 'tests'))

elif 'stationlite' == subsys:
    sys.argv.pop(1)

    _name = 'stationlite'
    _version = get_version('eidangservices/stationlite/__init__.py')
    _author = "Daniel Armbruster (ETH), Fabian Euchner (ETH)"
    _author_email = "daniel.armbruster@sed.ethz.ch, fabian.euchner@sed.ethz.ch"
    _description = ("EIDA NG StationLite webservice")

    _includes = ('eidangservices', 'eidangservices.utils',
                 'eidangservices.utils.tests',
                 '*.stationlite', 'stationlite.*', '*.stationlite.*')
    _entry_points = _entry_points_stationlite

    _deps = _deps_stationlite
    _data_files = _data_files_stationlite

    if sys.version_info[:2] < (3, 3):
        _deps.append('mock')
    _test_suites.append(os.path.join('eidangservices', 'stationlite', 'tests'))

elif 'mediator' == subsys:
    sys.argv.pop(1)
    raise RuntimeError("Mediator not packaged yet.")


if _test_suites == [os.path.join('eidangservices', 'utils', 'tests')]:
    # No subsystem deployment -> the full package is installed i.e. include all
    # tests packages
    _test_suites = find_packages(include=('*.tests', ))
    _test_suites = [suite.replace('.', os.path.sep) for suite in _test_suites]


if 'test' == sys.argv[1]:
    # remove testsuite duplicates
    try:
        idx = sys.argv.index('--addopts')
        pytest_args = sys.argv[idx+1]
        _test_suites = [suite for suite in _test_suites
                        if suite not in pytest_args.split(' ')]
    except IndexError:
        sys.argv.append('')
    except ValueError:
        pass

    if _test_suites:
        if '--addopts' in sys.argv:
            sys.argv[-1] += ' ' + ' '.join(_test_suites)
        else:
            sys.argv.append('--addopts')
            sys.argv.append(' '.join(_test_suites))


setup(
    name=_name,
    version=_version,
    author=_author,
    author_email=_author_email,
    description=_description,
    long_description=open('README.rst').read(),
    license="GPLv3",
    keywords="seismology waveforms federation mediation eida service",
    url="https://github.com/EIDA/mediatorws",
    platforms=['Linux', ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Flask",
        "Environment :: Web Environment",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Server",
        "Topic :: Scientific/Engineering", ],
    packages=find_packages(include=_includes),
    include_package_data=True,
    data_files=_data_files,
    install_requires=_deps,
    entry_points=_entry_points,
    zip_safe=False,
    setup_requires=['pytest-runner', ],
    tests_require=_test_deps,
    extras_require=_extras,
    # configure sphinx
    command_options={
        'build_sphinx': {
            'project': ('setup.py', _name),
            'version': ('setup.py', _version),
            'release': ('setup.py', _version)}},
)

# ---- END OF <setup.py> ----
