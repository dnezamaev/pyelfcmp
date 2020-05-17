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

from typing import Any, Tuple, List, Dict, Union, Optional
import io
import sys

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import Section
from elftools.elf.segments import Segment

from .structs import *
from .utils import *


def _group_segments(
    segments: List[Segment]) -> Dict[int, Dict[int, Segment]]:
    """
    Group segments by type (p_type) to dictionary. Value is dictionary
    where key is offset in file (p_offset) and value is Segment.
    Assuming offsets (p_offset) are unique for segments in group.
    """
    result = {}

    for segm in segments:

        type_ = segm["p_type"]
        offset = segm["p_offset"]

        if type_ not in result:
            result[type_] = {offset: segm.header}
        else:
            result[type_][offset] = segm.header

    return result
        

class ComparableElf(ELFFile):
    """
    Elf file that can be compared with another one via compare_to() method.
    :header_raw: dictionary of ELF header fields. ELFFile uses inner dictionary
        to store ei_ident so it is harder to compare.
    :other: ComparableElf compared with self by compare_to().
    :compare_result: ElfDiff - last result of compare_to().
    """

    def __init__(self, stream):
        super(ComparableElf, self).__init__(stream)
        self.other = None
        self.read_metadata()
        self.compare_result = ElfDiff()


    def read_metadata(self):
        """
        Prepare all inner data to compare. Call this method if file was changed.
        Since disk operations are far slower than memory and CPU, we read most
        required metadata (headers, blocks) once and store it in memory. 
        Real content (section, segment, blocks data) is not stored, 
        because it can be huge. So on next compare data will be ready. 
        """
        self.header_raw = {
            k: v for (k, v) in self.header.items() if k != "e_ident" }
        self.header_raw.update(
            {k: v for (k, v) in self.header["e_ident"].items()})
        self.sections = [*self.iter_sections()]
        self.segments = [*self.iter_segments()]
        self.used_blocks = self._get_used_blocks()
        self.not_used_blocks = self._get_not_used_blocks()


    def file_size(self):
        """ Returns size of file in bytes. """
        # Faster alternative, but not sure it works for all streams.
        # os.fstat(f.fileno()).st_size

        # Go to end of file, get position and restore it back.
        saved_position = self.stream.tell()
        self.stream.seek(0, io.SEEK_END)
        size = self.stream.tell()
        self.stream.seek(saved_position, io.SEEK_SET)
        return size


    def _compare_segments(self):
        """
        Compare segments. First group them by type in dictionary.
        Then compare groups of same type in left and rigth ELF files.
        Data is not compared since it is compared in sections and blocks.
        """
        left_segments = _group_segments(self.segments)
        right_segments = _group_segments(self.other.segments)

        self.compare_result.compared_segments = compare_dict(
            left_segments, right_segments, deep=True, include_same=False
            )
        

    def _compare_sections(self):
        """
        Compare sections by name, header and data content.
        """
        # Make dictionaries of sections {name: Section} to compare.
        # TODO: 
        #   In fact two sections may have same name. 
        #   Should be checked. Going to create such test file.
        #   But in such case its not clear how to compare sections?
        #   One option - sort by offset and compare by order: 1-1, 2-2, etc.
        #   Drawback of this method: new section in the beginning will give
        #   false positive diffs on all other sections. Like this:
        #   new-1, 1-2, 2-3, etc.
        sections_dict_1 = {s.name : s for s in self.sections}
        sections_dict_2 = {s.name : s for s in self.other.sections}

        # Compare by name to find unique sections.
        compared_section_names = compare_dict(
            sections_dict_1, sections_dict_2, 
            include_modified=False, deep=True)

        # Compare sections with same names (common sections).
        common_section_names = compared_section_names.common_keys
        modified_sections = dict()

        for section_name in common_section_names:

            section_1 = sections_dict_1[section_name]
            section_2 = sections_dict_2[section_name]

            header_1 = section_1.header
            header_2 = section_2.header

            # Section has dictionary-like interface for header. 
            compared_headers = compare_dict(
                header_1, header_2, include_same=False)

            # We are not interested in offset of name.
            compared_headers.modified.pop("sh_name", None)

            data_1 = section_1.data()
            data_2 = section_2.data()

            len_1 = len(data_1)
            len_2 = len(data_2)

            # Compare data byte to byte until first difference.
            diff_index = locate_array_diff(data_1, data_2)

            compared_section = SectionDiff(
                compared_headers if compared_headers.has_changes() else None,
                (len_1, len_2) if len_1 != len_2 else None,
                diff_index
                )

            if compared_section.has_changes():
                modified_sections[section_name] = compared_section

        result = AllSectionsDiff(
            left_new = compared_section_names.left_new,
            right_new = compared_section_names.right_new,
            modified = modified_sections
            )

        self.compare_result.compared_sections = result


    def _get_used_blocks(self) -> List[Block]:
        """
        Find all byte blocks used by ELF file and sort them by start offset: 
        ELF header, program header table, section header table and sections.
        Result will be stored in self.used_blocks and returned.
        :returns: sorted (by start offset) list of Block objects.
        """

        # ELF header, program header table, section header table.
        result = [
            Block(0, self["e_ehsize"], BlockType.ELF_HEADER, self, 
                self.header_raw),

            Block(self["e_phoff"], self["e_phentsize"] * self["e_phnum"], 
                BlockType.PROGRAM_HEADER_TABLE, self),

            Block(self["e_shoff"], self["e_shentsize"] * self["e_shnum"], 
                BlockType.SECTION_HEADER_TABLE, self),
            ]

        # Sections data.
        for section in self.sections:
            # Skip dummy sections.
            if (section["sh_size"] == 0 or section.is_null()
                or section["sh_type"] in ("SHT_NOBITS", "SHT_NULL") 
                ):
                continue

            result.append(
                Block(
                    section["sh_offset"], section["sh_size"],
                    BlockType.SECTION, self, section)
                )

        # Sort, save and return.
        result.sort(key=lambda b:b.start_offset)
        self.used_blocks = result
        return result


    def _get_not_used_blocks(self) -> List[Block]:
        """
        Find all byte blocks NOT used by ELF file and sort them by start offset.
        Result will be stored in self.not_used_blocks and returned.
        :returns: sorted (by start offset) list of Block objects.
        """

        # This method based on used blocks, so check they are found.
        if self.used_blocks == None:
            self._get_used_blocks()
        used_blocks = self.used_blocks

        result = []

        # Find all blocks between used blocks.
        if len(used_blocks) > 1:
            for i in range(len(used_blocks) - 1):
                cur_block = used_blocks[i]
                next_block = used_blocks[i + 1]

                if cur_block.end_offset() >= next_block.start_offset:
                    # Current and next blocks are sticked or overlapped.
                    # Nothing between them.
                    continue

                # There is space between current and next blocks.
                # So we found unused block, add it to result.
                result.append(Block(
                    cur_block.end_offset(), 
                    next_block.start_offset - cur_block.end_offset(),
                    BlockType.NOT_USED, self))

        # Check after the last used block.
        last_used_block = used_blocks[-1]
        file_size = self.file_size()

        # Is there anything after it in file?
        if last_used_block.end_offset() < file_size:
            result.append(Block(
                last_used_block.end_offset(), 
                file_size - last_used_block.end_offset(),
                BlockType.NOT_USED, self))

        # Sort, save and return.
        result.sort(key=lambda b:b.start_offset)
        self.not_used_blocks = result
        return result


    def _check_overlapped_blocks(
        self, 
        used_blocks: List[Block]
        ) -> List[Tuple[Block]]:
        """
        Check for used_blocks overlaps (2 blocks intersected).
        :used_blocks: list of used Block (occuped by headers or sections)
        :returns: list of tuple of overlapped Block
        """
        result = []

        for i in range(len(used_blocks) - 1):
            cur_block = used_blocks[i]
            next_block = used_blocks[i+1]

            if cur_block.last_offset() > next_block.start_offset:
                result.append((cur_block, next_block))

        return result
        

    def _compare_blocks(self):
        """
        Compare file blocks occuped by headers, sections = used_blocks.
        Also compare free blocks not occuped by anything = not_used_blocks.
        Also check for used_blocks overlaps (2 blocks intersected).
        """
        result = AllBlocksDiff()

        not_used_blocks_counts = (
            len(self.not_used_blocks), len(self.other.not_used_blocks))
        
        # Compare not used blocks only if counts are equal. 
        # Hard to say if there are any same or diff block otherwise.
        # Blocks should already be sorted by offset here.
        if not_used_blocks_counts[0] == not_used_blocks_counts[1]:

            for block_1, block_2 \
            in zip(self.not_used_blocks, self.other.not_used_blocks):

                block_diff = NotUsedBlockDiff()

                if block_1.size != block_2.size:
                    block_diff.data_sizes = (block_1.size, block_2.size)

                # We dont care about offset value, just data.
                block_diff.data_diff_offset = locate_array_diff(
                    block_1.data(), block_2.data())

                if block_diff.has_changes():
                    block_diff.left_block = block_1
                    block_diff.right_block = block_2
                    result.diffs_in_not_used.append(block_diff)

        else: # Diff in counts of not used blocks. Else None.
            result.counts_of_not_used = not_used_blocks_counts

        result.left_overlaps_in_used = self._check_overlapped_blocks(
            self.not_used_blocks)

        result.right_overlaps_in_used = self._check_overlapped_blocks(
            self.other.not_used_blocks)

        self.compare_result.compared_blocks = result


    def compare_to(self, other: "ComparableElf") -> ElfDiff:
        """
        Compare this instance to another.
        :returns: ElfDiff object.
        """
        self.other = other
        self.compare_result = ElfDiff()
        result = self.compare_result
        result.left_elf = self
        result.right_elf = other

        # ELFFile has dictionary-like interface for ELF header. 
        # Use header_raw with extracted ei_ident, for easy compare.
        result.compared_elf_headers = compare_dict(
            self.header_raw, self.other.header_raw, include_same=False)

        self._compare_segments()
        self._compare_sections()
        self._compare_blocks()

        return result
