import os
import shutil
import copy
import llnl.util.tty as tty
from spack.fetch_strategy import _needs_stage, FetchStrategy, NoArchiveFileError
from spack.util.compression import extension
from spack import *


class PyPip(Package):
    """The PyPA recommended tool for installing Python packages."""

    homepage = "https://pypi.python.org/pip"
    url      = "https://pypi.python.org/packages/source/p/pip/pip-7.1.2.tar.gz"

    version('8.1.1', '6b86f11841e89c8241d689956ba99ed7')

    extendable = True
    
    extends('python')
    depends_on('py-setuptools')

    def setup_dependent_package(self, module, ext_spec):
        module.pip = Executable(join_path(self.spec.prefix.bin, 'pip'))
        pkg = ext_spec.package
        version = pkg.versions[ext_spec.version]

        module.std_pip_args  = [
            '-f', 'file://{0}'.format(pkg.stage.path),
            '-b', join_path(pkg.stage.path, '{pip}-{version}'.format(**version)),
            '--prefix', ext_spec.prefix,
            '{pip}=={version}'.format(**version)
        ]
        mkdirp(ext_spec.prefix)
        
    def install(self, spec, prefix):
        python('./setup.py', 'install', '--prefix={0}'.format(self.prefix))



class PipFetchStrategy(FetchStrategy):
    """Fetch strategy that gets source code from a pip.
       Use like this in a package:

           version('name', pip='package-name')
    """
    enabled = True
    required_attributes = ['pip']

    def __init__(self, **kwargs):
        self.name = kwargs.get('pip', None)
        self.version = kwargs.get('version', None)
        self.pip_package = "{0}=={1}".format(self.name, self.version)
        
        super(PipFetchStrategy, self).__init__()
        self._pip = None
        
    @property
    def pip(self):
        if not self._pip:
            self._pip = which('pip', required=True)
        return self._pip

    @_needs_stage
    def fetch(self):
        self.stage.chdir()

        if os.path.exists(self.archive_file):
            tty.msg("Already downloaded %s" % self.archive_file)
            return

        args = []
        tty.msg("Trying to download pip package: {0}".format(self.pip_package))

        args = ['download', '--no-deps', '-d', self.stage.path, '{0}'.format(self.pip_package)]

        self.pip(*args)

    def __str__(self):
        return "[pip] {0}".format(self.pip_package)

    @property
    def archive_file(self):
        """Path to the source archive within this stage directory."""
        return join_path(self.stage.path, "{0}-{1}.tar.gz".format(self.name, self.version))

    @_needs_stage
    def expand(self):
        source_path = join_path(self.stage.path, "{0}-{1}".format(self.name, self.version))
        mkdirp(source_path)
        with open(join_path(source_path, 'not-empty'), 'w') as f:
            f.write('not empty')


    def archive(self, destination):
        """Just moves this archive to the destination."""
        if not self.archive_file:
            raise NoArchiveFileError("Cannot call archive() before fetching.")

        if not extension(destination) == extension(self.archive_file):
            raise ValueError("Cannot archive without matching extensions.")

        shutil.move(self.archive_file, destination)
