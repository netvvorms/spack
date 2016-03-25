from spack import *


class PyPsycopg2(Package):
    """The PyPA recommended tool for installing Python packages."""

    homepage = "https://pypi.python.org/pip"
    url = "https://pypi.python.org/packages/source/p/psycopg2/psycopg2-2.6.1.tar.gz"
    
    version('2.6.1', pip='psycopg2', version='2.6.1')

    extends('py-pip')

    def install(self, spec, prefix):
        pip('install', *std_pip_args)
