"""
EIDA NG Mediator/Ferderator webservices are built by means of the *namespace
package* approach. Hence, if desired, subpackages e.g. federator, mediator can
be distributed separately.

eidangservices implements the `pkgutil-style namespace packages
<https://packaging.python.org/guides/packaging-namespace-packages/#pkgutil-style-namespace-packages>`_
which provide compatibility both for Python 2.3+ and Python 3.

See also:
    - `https://packaging.python.org/guides/packaging-namespace-packages/`_

"""
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
