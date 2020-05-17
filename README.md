# pyelfcmp
Compares [ELF files](https://en.wikipedia.org/wiki/Executable_and_Linkable_Format), prints results in terminal and returns Python object for deep research of found differences. 

## What it compares?
Based on [pyelftools](https://github.com/eliben/pyelftools) Python package pyelfcmp allows you make deep compare of ELF files. How deep? According [ELF manual](http://man7.org/linux/man-pages/man5/elf.5.html) file next logic parts are compared.

### ELF header
Elf header is described in pyelftools as dictionary, so result will be:
* new keys on left (first) file
* new keys on right (second) file
* keys with modified values and its values

### Sections
Section is a byte array with some data or code. ELF file contains many sections. Each section has header (it is also a dictionary) and name (see "Known issues"). First we compare sets of section names for both files to find unique sections on left and right side. Then we compare headers and data of common sections (that belong to both files), so result will be:
* new sections on left file
* new sections on right file
* dictionary of common sections (with equal names). For each of them headers and data will are compared. As before, new keys on left and right, keys with not equal values will be found. Data arrays will be compared firstly by sizes and if sizes are equal then for contents.

### Blocks
Each ELF file part can be presented as block of bytes with starting offset and size. It is not hard to split file into such blocks: ELF header, program header table, section header table and sections. Let's call them "used blocks". Funny thing here is hidden between used blocks. Suddenly we can find unused blocks of data due to alignment. Often they are small, just few bytes, let's call them "not used blocks". When comparing files by binary diff, the problem for researcher here is to decide - is it used block or not used block. Because readelf and same tools will show you absolutly equal output for both files with different content, this problem cannot be solved by such tools.

Another problem with blocks is overlapping. In theory each byte belongs only one section. However due to incorrect compiler usage and other developer actions this rule can be broken. It can be done for example when one tries to manually append digital signature or conrols sum to file and calculates wrong offsets. I saw few such files, wasted much time to find out reason.

So result will be:
* not used blocks counts for both files
* list of not used blocks with non equal data (only if counts are equal in both files, otherwise it is hard to say something)
* list of used block pairs which are intersected in left file (overlapping blocks)
* same for right file

### Program header table (segment headers)
Segment is logical view it stores information  the  system  needs  to prepare the program for execution. Important thing to know about segments - they can overlap, it's okay. But as far as I know segments of one type should not overlap. Everything else for comparing is same to sections. Similarly segment header is a dictionary and segment has data. However we should not compare data because we did it on previous steps, all bytes are already compared. Before comparing, all segments will be grouped by type and then groups will be compared on left and right sides. Comparing inside groups are based on order in file (all segments are sorted by offset firstly). So result will be:
* new segments on left file for each group
* same for right file
* for common segments headers will be compares. As usual, new keys on left and rigth, not equal values for common keys will be found.

## How to use it?

### Installation
pyelfcmp is pure Python package, it depends on:

* Python 3.5+
* pyelftools

Python can be obtained [here](https://www.python.org/downloads). It is recommended to add path to system PATH variable due installation for new users.

pyelftools can be obtained with [pip3 tool](https://pypi.org/project/pip/) like this:

    pip3 install pyelftools

pyelfcmp is tested under Windows 10 with Python 3.5.4 and Ubuntu 18.04 with Python 3.6.9. Probably it will work on versions below, please let me know if it does.

### Quick start
Launch run.sh or run.bat to see how it works. Or do it manually like this:

    python3 examples/main.py path/to/elf_1 path/to/elf_2

You should see compare result for each part described in "What it compares" part of this document.

If you write in Python, main class to deal with is ComparableElf, it can be found in elfcmp/elfcmp.py. It is initialised with data stream, like open("file"). After that you call compare_to() method with another ComparableElf instance as argument. Result will be ElfDiff instance, defined in elfcmp/structs.py, some more interesting structs are defined there too, also you can see in elfcmp/utils.py to see DictDiff (stored dictionaries compare result). For more details see classes docstrings, comments and tests. WARNING: on first versions I do not guarantee API backward compatibility, it can be changed in any new release, please be careful.

Tests can be found in test directory. Small test files generator can be found in test/generator directory.

## Known issues
Each section have text name which probably must be unique, but there is no guarantee. In fact two sections may have same name. But in such case its not clear how to compare sections. One option is to sort sections by offset and compare in order: 1-1, 2-2, etc. Drawback of this method: new section in the beginning will give false positive diffs on all other sections. Like this: new-1, 1-2, 2-3, etc. So we assume sections have unique names for now, maybe later I will find way to deal with it. If you have ideas, feel free to write me.

## License

Copyright (C) 2020 Dmitriy Nezamaev (dnezamaev@gmail.com).

pyelfcmp is free source software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

pyelfcmp is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with pyelfcmp. If not, see <http://www.gnu.org/licenses/>.
