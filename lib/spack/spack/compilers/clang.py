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
import re
import spack.compiler as cpr
from spack.compiler import *
from spack.util.executable import *

class Clang(Compiler):
    # Subclasses use possible names of C compiler
    cc_names = ['clang']

    # Subclasses use possible names of C++ compiler
    cxx_names = ['clang++']

    # Subclasses use possible names of Fortran 77 compiler
    f77_names = []

    # Subclasses use possible names of Fortran 90 compiler
    fc_names = []

    # Named wrapper links within spack.build_env_path
    link_paths = { 'cc'  : 'clang/clang',
                   'cxx' : 'clang/clang++',
                   # Use default wrappers for fortran, in case provided in compilers.yaml
                   'f77' : 'f77',
                   'fc'  : 'f90' }

    @classmethod
    def default_version(self, comp):
        """The '--version' option works for clang compilers.
           On most platforms, output looks like this::

               clang version 3.1 (trunk 149096)
               Target: x86_64-unknown-linux-gnu
               Thread model: posix

          On Mac OS X, it looks like this:

               Apple LLVM version 7.0.2 (clang-700.1.81)
               Target: x86_64-apple-darwin15.2.0
               Thread model: posix

        """
        if comp not in cpr._version_cache:
            compiler = Executable(comp)
            output = compiler('--version', output=str, error=str)

            ver = 'unknown'
            match = re.search(r'^Apple LLVM version ([^ )]+)', output)
            if match:
                # Apple's LLVM compiler has its own versions, so suffix them.
                ver = match.group(1) + '-apple'
            else:
                # Normal clang compiler versions are left as-is
                match = re.search(r'^clang version ([^ )]+)', output)
                if match:
                    ver = match.group(1)

            cpr._version_cache[comp] = ver

        return cpr._version_cache[comp]
