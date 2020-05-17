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

from collections.abc import Mapping
import operator
from typing import List, Set, Dict, Tuple, Union

ByteArray = Union[bytes, bytearray]


def is_integer(x) -> bool:
    """
    Check any object if it is int or inherited.
    """
    return isinstance(x, int) and not isinstance(x, bool)


def locate_array_diff(
    byte_array_1: ByteArray, byte_array_2: ByteArray) -> int:
    """ Find index of first non-equal byte of two arrays.
    :returns: -1 if arrays are equal; length of the shortest array if their
    common parts are equal, but lengths differ; index of first non-equal byte 
    if length are same, but contents are not.
    """

    len_1 = len(byte_array_1)
    len_2 = len(byte_array_2)

    # Assume lengths may be different.
    length = min(len_1, len_2)

    # Check bytes in common length parts.
    for i in range(length):
        if byte_array_1[i] != byte_array_2[i]:
            return i

    # If we are here, everything before is ok.
    # So difference is length.
    if len_1 != len_2:
        return length

    # Arrays are equal.
    return -1


class DictDiff:
    """
    :left_new: set of new keys in first dictionary;
    :right_new: set of new keys in second dictionary;
    :common_keys: set of keys belong to both dictionaries;
    :modified: dictionary of changes - key : tuple of values (left, right);
    :same: set of keys with equal values 
    """
    def __init__(
        self,
        left_new:Set = set(),
        right_new:Set = set(),
        common_keys = set(),
        modified:Dict = dict(),
        same:Set = set()
        ):

        self.left_new = left_new
        self.right_new = right_new
        self.common_keys = common_keys
        self.modified = modified
        self.same = same


    # Uncommenting this lead to double to_string() calls. Dunno why.
    def __str__(self):
        return self.to_string()


    def has_changes(self) -> bool:
        """
        Check if any changes were found.
        """
        return self.left_new or self.right_new or self.modified


    def to_string(
        self, 
        indent: str = "",
        numbers_format: str = "02X", 
        header: str = "",
        sub_headers: List[str] = ["Left new:", "Right new:", "Modified:"]
        ):
        """
        Print human readable result of dictionaries comparison.
        :indent: string to insert at start of lines
        :numbers_format: how to format integer values, default is hex
        :header: first line if any changes found and header is not empty
        :sub_headers: list of header for each compare result (left_new, 
            right_new, modified). If result is empty, header and result will
            not be printed.
        """
        # Collect result string parts here.
        result = []

        if self.has_changes() and header:
            result.append(header)

        if self.left_new:
            result.append("{}{}".format(sub_headers[0], str(self.left_new)))

        if self.right_new:
            result.append("{}{}".format(sub_headers[1], str(self.right_new)))

        if self.modified:
            for key in self.modified:
                # Collect modified parts here.
                mod_res = []
                mod_res.append("{}{}: ".format(sub_headers[2], key))

                mod_value = self.modified[key]
                mod_separator = ""

                # Check if values were dictionaries too.
                if isinstance(mod_value, tuple): 
                    # No. mod_res is tuple.
                    v1,v2 = mod_value
                    mod_res.append(
                        "{},{}".format(
                            format(v1, numbers_format)\
                                if is_integer(v1) else str(v1),
                            format(v2, numbers_format)\
                                if is_integer(v2) else str(v2)
                            )
                        )
                else:
                    # Yes. mod_res is DictDiff.
                    mod_res.append(mod_value.to_string(indent=indent+"\t"))
                    mod_separator = "\n"

                result.append(mod_separator.join(mod_res))

        result_str = indent if result else ""
        result_str += "\n{}".format(indent).join(result)

        return result_str 


def compare_dict(
    d1: dict, d2: dict, deep=False,
    include_modified=True, include_same=True, 
    compare_function=operator.eq) -> DictDiff:
    """ Compare dictionaries by keys and values.
    :d1: first dictionary
    :d2: second dictionary
    :include_modified: add dictionary of modified to result 
        {keys:(left_value, rigth_value)} 
    :include_same: add set of keys with same values to result
    :deep: 
        True - if values are dictionaries too 
            then apply this function to them again. 
        False - just return tuple of full dictionaries.
    :compare_function: function to compare values
    :returns: see DictDiff
    """

    # Find new keys by intersection and substraction.
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    d1_new = d1_keys - d2_keys
    d2_new = d2_keys - d1_keys

    # Find same and modified keys.
    same = set()
    modified = {}

    for key in intersect_keys:

        value_1 = d1[key]
        value_2 = d2[key]

        if compare_function(value_1, value_2):
            if include_same:
                same.add(key)

        elif include_modified:
            # Check if value is kind of dictionary too and we go deeper.
            if (deep 
                and isinstance(value_1, Mapping) 
                and isinstance (value_2, Mapping)
                ):
                # Compare inner dictionary same way.
                modified[key] = compare_dict(
                    value_1, value_2,
                    include_same=include_same, deep=deep)
            else:
                modified[key] = (value_1, value_2)

    return DictDiff(d1_new, d2_new, intersect_keys, modified, same)
