#!/usr/bin/python3

# Copyright (C) 2020 Dmitriy Nezamaev (dnezamaev@gmail.com).
#
# This file is part of py-elfcmp.
#
# py-elfcmp is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# py-elfcmp is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with py-elfcmp. If not, see <http://www.gnu.org/licenses/>.

from typing import Any, Tuple, List, Dict, Union, Optional
import io
import sys

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import Section
from elftools.elf.segments import Segment

# Allows import local files when running from the root of project.
sys.path.insert(1, ".")

from elfcmp.elfcmp import *

if __name__ == '__main__':

    if len(sys.argv) < 3:
        print("No arguments")
    else:
        with\
        open(sys.argv[1], 'rb') as file_1,\
        open(sys.argv[2], 'rb') as file_2:

            left_elf = ComparableElf(file_1)
            right_elf = ComparableElf(file_2)

            # print(type(left_elf.header).mro())
            # for s in left_elf.segments:
            #     print(s["p_type"], s["p_offset"], s["p_offset"] + s["p_filesz"])
            # exit()

            cmp_result = left_elf.compare_to(right_elf)
            print(cmp_result)

