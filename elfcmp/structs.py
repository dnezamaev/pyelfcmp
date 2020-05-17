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

from enum import Enum
from typing import Tuple, List, Dict

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import Section

from .utils import *


# TODO: make class indents in __str__() methods like in AllSectionsDiff and 
#   NotUsedBlockDiff.

# How to print numbers.
numbers_format = "02X"


class SectionDiff:
    """
    Describes Section that belongs to both ELF files but differs by one or more
    attributes listed below.

    :headers: DictDiff for Section.header dictionaries, 
        None if equal
    :data_sizes: tuple of sizes, None if equal
    :data_diff_offset: -1 if data arrays are equal; length of the shortest
        array if their common parts are equal, but lengths differ; index of
        first non-equal byte if length are same, but contents are not.
    """
    def __init__(
        self, 
        headers: DictDiff = None,
        data_sizes: Tuple[int, int] = None,
        data_diff_offset: int = -1):

        self.headers = headers
        self.data_sizes = data_sizes
        self.data_diff_offset = data_diff_offset


    def has_changes(self):
        """ Check if any changes were found.  """
        return not (
            self.headers is None and self.data_sizes is None 
            and self.data_diff_offset == -1)


    def __str__(self):
        indent = "\t\t"
        inner_indent = "\t\t\t"
        result = []

        if self.headers is not None:
            result.append(
                "Headers:\n{}.".format(
                    self.headers.to_string(indent=inner_indent)))

        if self.data_sizes is not None:
            result.append(
                "Data sizes: {},{}".format(
                    format(self.data_sizes[0], numbers_format), 
                    format(self.data_sizes[1], numbers_format))
                )

        if self.data_diff_offset != -1:
            result.append(
                "First data diff at: {}".format(
                    format(self.data_diff_offset, numbers_format)))

        result_str = indent if result else ""
        result_str += "\n{}".format(indent).join(result)

        return result_str 


class AllSectionsDiff:
    """
    Describes Sections that not equal in ELF files.

    :left_new: set of first file unique sections names 
    :right_new: set of second file unique sections names 
    :modified: dictionary of common sections (with equal names), 
        values are SectionDiff
    """
    def __init__(
        self,
        left_new: Set[str] = None,
        right_new: Set[str] = None,
        modified: Dict[str, SectionDiff] = None
        ):

        self.left_new = left_new
        self.right_new = right_new
        self.modified = modified


    def has_changes(self) -> bool:
        """
        Check if any changes were found.
        """
        return self.left_new or self.right_new or self.modified


    def __str__(self):
        indent = "\t"
        result = []

        if not self.has_changes():
            return ""

        if self.left_new:
            result.append("Left new sections: {}".format(str(self.left_new)))

        if self.right_new:
            result.append("Right new sections: {}".format(str(self.right_new)))

        if self.modified:
            for sec_name in self.modified:
                result.append(
                    "Section {}:\n{}".format(
                        sec_name, str(self.modified[sec_name])))

        result_str = indent if result else ""
        result_str += "\n{}".format(indent).join(result)

        return result_str 


class BlockType(Enum):
    """ Describes type of Block. """
    NOT_USED             = 0
    ELF_HEADER           = 1
    PROGRAM_HEADER_TABLE = 2
    SECTION_HEADER_TABLE = 3
    SECTION              = 4


class Block:
    """
    Describes block of bytes in elf file. All offsets from the beginning of file.

    :elf: reference to ELFFile object
    :block_type: type of this block, see BlockType
    :start_offset: index of first byte of block in data_stream
    :size: size of block in bytes
    :object_: reference to object (like Section, elf header dict, ...)
    """

    def __init__(
        self, start_offset: int, size: int, block_type: BlockType, 
        elf: ELFFile, object_=None):
        """
        :elf: reference to ELFFile object
        :block_type: type of this block, see BlockType
        :start_offset: index of first byte of block in data_stream
        :size: size of block in bytes
        :object_: reference to object (like Section, elf header dict, ...)
        """
        self.elf = elf
        self.block_type = block_type
        self.start_offset = start_offset
        self.size = size
        self.object_ = object_


    def last_offset(self) -> int:
        """ Index of last byte of block in data_stream. """
        return self.start_offset + self.size - 1


    def end_offset(self) -> int:
        """ Index of next to the last byte of block in data_stream. """
        return self.start_offset + self.size


    def data(self) -> bytes:
        """ Get data decsribed by this block.  """
        self.elf.stream.seek(self.start_offset)
        return self.elf.stream.read(self.size)


    def __str__(self) -> str:
        info = ""

        if self.block_type == BlockType.SECTION:
            info = "({})".format(self.object_.name)

        return (
            "{}{}:[{}-{}]".format(
                self.block_type, info,
                format(self.start_offset, '02X'),
                format(self.last_offset(), '02X'))
            )


class NotUsedBlockDiff(object):
    """
    Describes difference in not used block that belongs to both ELF files.

    :indent: class attribute defines indentation for __str__()
    :left_block: reference to left Block
    :right_block: reference to left Block
    :data_sizes: tuple of block sizes. None if equal.
    :data_diff_offset: -1 if data arrays are equal; length of the shortest
        array if their common parts are equal, but lengths differ; index of
        first non-equal byte if length are same, but contents are not.
    """

    indent = ""

    def __init__(
        self,
        left_block: Block = None,
        right_block: Block = None,
        data_sizes: Tuple[int, int] = None,
        data_diff_offset: int = -1
        ):

        self.left_block = left_block
        self.right_block = right_block
        self.data_sizes = data_sizes
        self.data_diff_offset = data_diff_offset


    def has_changes(self) -> bool:
        """
        Check if any changes were found.
        """
        return self.data_sizes is not None or self.data_diff_offset != -1


    def __str__(self):
        result = []

        if not self.has_changes():
            return ""

        if self.data_sizes is not None:
            result.append(
                "Data sizes: {},{}".format(
                    format(self.data_sizes[0], numbers_format),
                    format(self.data_sizes[1], numbers_format)))

        if self.data_diff_offset != -1:
            result.append(
                "First data diff at: {}".format(
                    format(self.data_diff_offset, numbers_format)))

        result_str = NotUsedBlockDiff.indent if result else ""
        result_str += "\n{}".format(NotUsedBlockDiff.indent).join(result)

        return result_str 

           
class AllBlocksDiff(object):
    """
    Describes results of blocks compare.

    :left_overlaps_in_used: list of block tuples that points to intersected 
        memory regions (what is forbidden by elf manual) on left file.
    :right_overlaps_in_used: same on right file.
    :counts_of_not_used: tuple of not used blocks counts for both files,
        None if equal.
    :diffs_in_not_used: list of not used blocks with non equal data
    """
    indent = ""

    def __init__(
        self,
        left_overlaps_in_used: List[Tuple[Block]] = [],
        right_overlaps_in_used: List[Block] = [],
        counts_of_not_used: Tuple[int, int] = None,
        diffs_in_not_used: List[NotUsedBlockDiff] = []
        ):

        self.left_overlaps_in_used = left_overlaps_in_used
        self.right_overlaps_in_used = right_overlaps_in_used
        self.counts_of_not_used = counts_of_not_used
        self.diffs_in_not_used = diffs_in_not_used
        
        
    def has_changes(self) -> bool:
        """
        Check if any changes were found.
        """
        return (self.left_overlaps_in_used or self.right_overlaps_in_used 
            or self.counts_of_not_used is not None
            or self.diffs_in_not_used)


    def __str__(self):
        result = []

        if not self.has_changes():
            return ""

        if self.left_overlaps_in_used:
            result.append("Left overlaps: {}".format(
                str(self.left_overlaps_in_used)))

        if self.right_overlaps_in_used:
            result.append("Right overlaps: {}".format(
                str(self.right_overlaps_in_used)))

        if self.counts_of_not_used is not None:
            result.append(
                "Counts of not used blocks: {}".format(
                    str(self.counts_of_not_used)))

        if self.diffs_in_not_used:
            sub_result = []
            result.append("Different not used blocks:")

            saved_indent = NotUsedBlockDiff.indent
            NotUsedBlockDiff.indent = AllBlocksDiff.indent + "\t"

            for diff in self.diffs_in_not_used:
                sub_result.append(str(diff))

            NotUsedBlockDiff.indent = saved_indent

            result.append("\n".join(sub_result))

        result_str = AllBlocksDiff.indent if result else ""
        result_str += "\n".join(result)

        return result_str 


class ElfDiff:
    """
    Result of ELF files comparison.

    :left_elf: first compared elf, self in compare_to()
    :right_elf: second compared elf, other in compare_to()
    :compared_elf_headers: DictDiff of ELF header values
    :compared_segments: DictDiff of segments
    :compared_sections: AllSectionsDiff
    :compared_blocks: AllBlocksDiff
    """
    def __init__(
        self, 
        left_elf: "ComparableElf" = None,
        right_elf: "ComparableElf" = None,
        compared_elf_headers: DictDiff = None,
        compared_segments: DictDiff = None,
        compared_sections: AllSectionsDiff = None,
        compared_blocks: AllBlocksDiff = None
        ):

        self.left_elf = left_elf
        self.right_elf = right_elf
        self.compared_elf_headers = compared_elf_headers
        self.compared_segments = compared_segments
        self.compared_sections = compared_sections
        self.compared_blocks = compared_blocks


    def has_changes(self) -> bool:
        """
        Check if any changes were found.
        """
        return (
            self.compared_elf_headers.has_changes()
            or self.compared_segments.has_changes()
            or self.compared_sections.has_changes()
            or self.compared_blocks.has_changes()
            )


    def __str__(self):
        result = []

        if not self.has_changes():
            return ""

        if self.compared_elf_headers.has_changes():
            result.append(
                "ELF headers start\n"
                "{}\n"
                "ELF headers end\n".format(
                    str(self.compared_elf_headers)))

        if self.compared_segments.has_changes():
            result.append(
                "Segments start\n"
                "{}\n"
                "Segments end\n".format(
                    str(self.compared_segments)))

        if self.compared_sections.has_changes():
            result.append(
                "Sections start\n"
                "{}\n"
                "Sections end\n".format(
                    str(self.compared_sections)))

        if self.compared_blocks.has_changes():
            result.append(
                "Blocks start\n"
                "{}\n"
                "Blocks end\n".format(
                    str(self.compared_blocks)))

        return "\n".join(result)

