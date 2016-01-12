##############################################################################
# Copyright (c) 2013, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Spack.
# Written by Todd Gamblin, tgamblin@llnl.gov, All rights reserved.
# LLNL-CODE-647188
#
# For details, see https://github.com/llnl/spack
# Please also see the LICENSE file for our notice and the LGPL.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License (as published by
# the Free Software Foundation) version 2.1 dated February 1999.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the IMPLIED WARRANTY OF
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the terms and
# conditions of the GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##############################################################################
"""This module contains code for creating environment modules, which
can include dotkits, tcl modules, lmod, and others.

The various types of modules are installed by post-install hooks and
removed after an uninstall by post-uninstall hooks.  This class
consolidates the logic for creating an abstract description of the
information that module systems need.  Currently that includes a
number of directories to be appended to paths in the user's environment:

  * /bin directories to be appended to PATH
  * /lib* directories for LD_LIBRARY_PATH
  * /man* and /share/man* directories for MANPATH
  * the package prefix for CMAKE_PREFIX_PATH

This module also includes logic for coming up with unique names for
the module files so that they can be found by the various
shell-support files in $SPACK/share/spack/setup-env.*.

Each hook in hooks/ implements the logic for writing its specific type
of module file.
"""
__all__ = ['EnvModule', 'Dotkit', 'TclModule']

import os
import re
import textwrap
import shutil
from glob import glob

import llnl.util.tty as tty
from llnl.util.filesystem import join_path, mkdirp

import spack

import spack.compilers  # Needed by LmodModules


"""Registry of all types of modules.  Entries created by EnvModule's
   metaclass."""
module_types = {}


def print_help():
    """For use by commands to tell user how to activate shell support."""

    tty.msg("This command requires spack's shell integration.",
            "",
            "To initialize spack's shell commands, you must run one of",
            "the commands below.  Choose the right command for your shell.",
            "",
            "For bash and zsh:",
            "    . %s/setup-env.sh" % spack.share_path,
            "",
            "For csh and tcsh:",
            "    setenv SPACK_ROOT %s"    % spack.prefix,
            "    source %s/setup-env.csh" % spack.share_path,
            "")


class EnvModule(object):
    name = 'env_module'

    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            type.__init__(cls, name, bases, dict)
            if cls.name != 'env_module':
                module_types[cls.name] = cls


    def __init__(self, spec=None):
        # category in the modules system
        # TODO: come up with smarter category names.
        self.category = "spack"

        # Descriptions for the module system's UI
        self.short_description = ""
        self.long_description = ""

        # dict pathname -> list of directories to be prepended to in
        # the module file.
        self._paths = None
        self.spec = spec


    @property
    def paths(self):
        if self._paths is None:
            self._paths = {}

            def add_path(path_name, directory):
                path = self._paths.setdefault(path_name, [])
                path.append(directory)

            # Add paths if they exist.
            for var, directory in [
                    ('PATH', self.spec.prefix.bin),
                    ('MANPATH', self.spec.prefix.man),
                    ('MANPATH', self.spec.prefix.share_man),
                    ('LIBRARY_PATH', self.spec.prefix.lib),
                    ('LIBRARY_PATH', self.spec.prefix.lib64),
                    ('LD_LIBRARY_PATH', self.spec.prefix.lib),
                    ('LD_LIBRARY_PATH', self.spec.prefix.lib64),
                    ('PKG_CONFIG_PATH', join_path(self.spec.prefix.lib, 'pkgconfig')),
                    ('PKG_CONFIG_PATH', join_path(self.spec.prefix.lib64, 'pkgconfig'))]:

                if os.path.isdir(directory):
                    add_path(var, directory)

            # Add python path unless it's an actual python installation
            # TODO: is there a better way to do this?
            if self.spec.name != 'python':
                site_packages = glob(join_path(self.spec.prefix.lib, "python*/site-packages"))
                if site_packages:
                    add_path('PYTHONPATH', site_packages[0])

            if self.spec.package.extends(spack.spec.Spec('ruby')):
              add_path('GEM_PATH', self.spec.prefix)

            # short description is just the package + version
            # TODO: maybe packages can optionally provide it.
            self.short_description = self.spec.format("$_ $@")

            # long description is the docstring with reduced whitespace.
            if self.spec.package.__doc__:
                self.long_description = re.sub(r'\s+', ' ', self.spec.package.__doc__)

        return self._paths


    def write(self):
        """Write out a module file for this object."""
        module_dir = os.path.dirname(self.file_name)
        if not os.path.exists(module_dir):
            mkdirp(module_dir)

        # If there are no paths, no need for a dotkit.
        if not self.paths:
            return

        with open(self.file_name, 'w') as f:
            self._write(f)


    def _write(self, stream):
        """To be implemented by subclasses."""
        raise NotImplementedError()


    @property
    def file_name(self):
        """Subclasses should implement this to return the name of the file
           where this module lives."""
        raise NotImplementedError()


    @property
    def use_name(self):
        """Subclasses should implement this to return the name the
           module command uses to refer to the package."""
        raise NotImplementedError()


    def remove(self):
        mod_file = self.file_name
        if os.path.exists(mod_file):
            shutil.rmtree(mod_file, ignore_errors=True)


class Dotkit(EnvModule):
    name = 'dotkit'
    path = join_path(spack.share_path, "dotkit")

    @property
    def file_name(self):
        return join_path(Dotkit.path, self.spec.architecture,
                         self.spec.format('$_$@$%@$+$#.dk'))

    @property
    def use_name(self):
        return self.spec.format('$_$@$%@$+$#')


    def _write(self, dk_file):
        # Category
        if self.category:
            dk_file.write('#c %s\n' % self.category)

        # Short description
        if self.short_description:
            dk_file.write('#d %s\n' % self.short_description)

        # Long description
        if self.long_description:
            for line in textwrap.wrap(self.long_description, 72):
                dk_file.write("#h %s\n" % line)

        # Path alterations
        for var, dirs in self.paths.items():
            for directory in dirs:
                dk_file.write("dk_alter %s %s\n" % (var, directory))

        # Let CMake find this package.
        dk_file.write("dk_alter CMAKE_PREFIX_PATH %s\n" % self.spec.prefix)


class TclModule(EnvModule):
    name = 'tcl'
    path = join_path(spack.share_path, "modules")

    @property
    def file_name(self):
        return join_path(TclModule.path, self.spec.architecture, self.use_name)


    @property
    def use_name(self):
        return self.spec.format('$_$@$%@$+$#')


    def _write(self, m_file):
        # TODO: cateogry?
        m_file.write('#%Module1.0\n')

        # Short description
        if self.short_description:
            m_file.write('module-whatis \"%s\"\n\n' % self.short_description)

        # Long description
        if self.long_description:
            m_file.write('proc ModulesHelp { } {\n')
            doc = re.sub(r'"', '\"', self.long_description)
            m_file.write("puts stderr \"%s\"\n" % doc)
            m_file.write('}\n\n')

        # Path alterations
        for var, dirs in self.paths.items():
            for directory in dirs:
                m_file.write("prepend-path %s \"%s\"\n" % (var, directory))

        m_file.write("prepend-path CMAKE_PREFIX_PATH \"%s\"\n" % self.spec.prefix)


class LmodModule(EnvModule):
    name = 'lmod'
    path = join_path(spack.share_path, "lmod", "modulefiles")

    def __init__(self, spec=None):
        super(LmodModule, self).__init__(spec)
        # Sets tha appropriate category to be used with the 'family' function
        if self.spec.name in spack.compilers.supported_compilers():
            self.family = 'compiler'
        elif self.spec.package.provides('mpi'):
            self.family = 'mpi'
        else:
            self.family = None
        # Sets the root directory for this architecture
        self.modules_root = join_path(LmodModule.path, self.spec.architecture)

    @property
    def file_name(self):
        if self._use_system_compiler() and not self._is_mpi_dependent():
            # If the module is installed using the system compiler and does not need MPI put the modulefile in 'Core'
            hierarchy_name = 'Core'
        elif not self._is_mpi_dependent():
            # If the module is serial and built using a compiler other than the system one,
            # put the modulefile in '<Compiler>/<Version>'
            hierarchy_name = self._compiler_module_directory(self.spec.compiler.name, self.spec.compiler.version)
        else:
            # If the module is MPI parallel then put the modulefile in
            # '<MPI>/<MPI-Version>/<Compiler/<Compiler-Version>'
            compiler = self.spec.compiler
            mpi = self.spec['mpi']
            hierarchy_name = self._mpi_module_directory(compiler.name, compiler.version, mpi.name, mpi.version)
        fullname = join_path(self.modules_root, hierarchy_name, self.use_name + '.lua')
        return fullname

    @property
    def use_name(self):
        return join_path(self.spec.name, str(self.spec.version))

    @staticmethod
    def _compiler_module_directory(name, version):
        return '{compiler_name}/{compiler_version}'.format(
                compiler_name=name,
                compiler_version=version
            )

    @staticmethod
    def _mpi_module_directory(compiler_name, compiler_version, mpi_name, mpi_version):
        return '{mpi_name}/{mpi_version}/{compiler_name}/{compiler_version}'.format(
                mpi_name=mpi_name,
                mpi_version=mpi_version,
                compiler_name=compiler_name,
                compiler_version=compiler_version
            )

    def _write(self, m_file):
        # Header as in
        # https://www.tacc.utexas.edu/research-development/tacc-projects/lmod/advanced-user-guide/more-about-writing-module-files
        m_file.write("-- -*- lua -*-\n")
        # Short description -> whatis()
        if self.short_description:
            m_file.write("whatis([[Name : {name}]])\n".format(name=self.spec.name))
            m_file.write("whatis([[Version : {version}]])\n".format(version=self.spec.version))

        # Long description -> help()
        if self.long_description:
            doc = re.sub(r'"', '\"', self.long_description)
            m_file.write("help([[{documentation}]])\n".format(documentation=doc))

        # Path alterations
        for var, dirs in self.paths.items():
            for directory in dirs:
                m_file.write("prepend_path(\"{variable}\", \"{directory}\")\n".format(
                    variable=var,
                    directory=directory)
                )
        m_file.write("prepend_path(\"CMAKE_PREFIX_PATH\", \"{cmake_prefix}\")\n".format(cmake_prefix=self.spec.prefix))

        # Add family protection
        if self.family is not None:
            m_file.write("family(\"{family}\")\n".format(family=self.family))

        # Prepend path if family is 'compiler' or 'mpi'
        if self.family is 'compiler':
            hierarchy_name = self._compiler_module_directory(self.spec.name, self.spec.version)
            fullname = join_path(self.modules_root, hierarchy_name)
            m_file.write("prepend_path(\"MODULEPATH\", \"{compiler_directory}\")".format(compiler_directory=fullname))
        elif self.family is 'mpi':
            s = self.spec
            hierarchy_name = self._mpi_module_directory(s.compiler.name, s.compiler.version, s.name, s.version)
            fullname = join_path(self.modules_root, hierarchy_name)
            m_file.write("prepend_path(\"MODULEPATH\", \"{compiler_directory}\")".format(compiler_directory=fullname))

    def _use_system_compiler(self):
        """
        True if the spec uses the OS default compiler

        :return: True or False
        """
        # FIXME: How can I check if a spec has been constructed using the OS default compiler?
        compiler = spack.compilers.compiler_for_spec(self.spec.compiler)
        compiler_directory = os.path.dirname(compiler.cc)
        if spack.prefix in compiler_directory:
            return False
        return True

    def _is_mpi_dependent(self):
        """
        Traverse the DAG (excluding root) to see if the spec depends on MPI

        :return: True or False
        """
        for item in self.spec.traverse(root=False):
            if 'mpi' in item:
                return True
        return False
