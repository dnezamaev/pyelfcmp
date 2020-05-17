#!/usr/bin/python3

# Copyright (C) 2020 Dmitriy Nezamaev (dnezamaev@gmail.com).
#
# This file is part of pyelfcmp.
#
# pyelfcmp is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyelfcmp is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyelfcmp. If not, see <http://www.gnu.org/licenses/>.

import unittest
import sys

# Allows import local files when running from the root of project.
sys.path.insert(1, ".")

from elfcmp.elfcmp import ComparableElf
from elfcmp.structs import *
from elfcmp.utils import *


class TestUtils(unittest.TestCase):

    def test_locate_array_diff(self):

        array_1 = bytes([1,2,3])
        array_1_copy = bytes([1,2,3])
        array_2 = bytes([1,1,3])
        array_3 = bytes([1,2,3,4])
        array_4 = bytes([1,1,3,4])

        self.assertEqual(-1, locate_array_diff(array_1, array_1_copy))
        self.assertEqual(1, locate_array_diff(array_1, array_2))
        self.assertEqual(3, locate_array_diff(array_1, array_3))
        self.assertEqual(1, locate_array_diff(array_1, array_4))


def compare_elf_files(
    left_file: str, right_file: str, print_result: bool=False) -> ElfDiff:

    with open(left_file, 'rb') as file_1, open(right_file, 'rb') as file_2:

        left_elf = ComparableElf(file_1)
        right_elf = ComparableElf(file_2)

        result = left_elf.compare_to(right_elf)

        if print_result:
            print(left_file, right_file)
            print(result)

        return result


class TestElfCmp(unittest.TestCase):
    
    def test_elf_header_diff(self):
        left = "test/data/elf_header/1"
        right = "test/data/elf_header/2"
        result = compare_elf_files(left, right)
        
        self.assertFalse(result.compared_segments.has_changes())
        self.assertFalse(result.compared_sections.has_changes())
        self.assertFalse(result.compared_blocks.has_changes())

        hdr_diff = result.compared_elf_headers
        self.assertTrue(hdr_diff.has_changes())
        self.assertFalse(hdr_diff.left_new)
        self.assertFalse(hdr_diff.right_new)

        modified = hdr_diff.modified
        self.assertEqual(len(modified), 2)
        self.assertTrue("EI_ABIVERSION" in modified and "EI_OSABI" in modified)
        self.assertTupleEqual(modified["EI_ABIVERSION"], (0x00, 0x08))
        self.assertTupleEqual(
            modified["EI_OSABI"],
            ("ELFOSABI_SYSV", "ELFOSABI_AIX"))


    # TODO
    def test_defined_string(self):
        f1 = "test/data/defined_string/1"
        f2 = "test/data/defined_string/2"
        f3 = "test/data/defined_string/3"
        # result = compare_elf_files(f1, f2, True)
        # result = compare_elf_files(f1, f3, True)
        

    # TODO
    def test_build_id(self):
        f1 = "test/data/build_id/with"
        f2 = "test/data/build_id/without"
        # e1 = ComparableElf(open(f1, "rb"))
        # for s in e1.sections:
        #     print(s.header)
        result = compare_elf_files(f1, f2, True)
        


if __name__ == '__main__':
    unittest.main()
