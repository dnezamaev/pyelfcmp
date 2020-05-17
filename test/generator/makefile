out_dir=../data

all: defined_string_1 defined_string_2 defined_string_3\
	with_build_id without_build_id

defined_string_1: main.c
	gcc -o $(out_dir)/defined_string/1 -DTEST_STRING='"Hello, World!"' main.c

defined_string_2: main.c
	gcc -o $(out_dir)/defined_string/2 -DTEST_STRING='"Hello, WORLD!"' main.c

defined_string_3: main.c
	gcc -o $(out_dir)/defined_string/3 -DTEST_STRING='"Test"' main.c

with_build_id:
	gcc -o $(out_dir)/build_id/with main.c

without_build_id:
	gcc -Wl,--build-id=none -o $(out_dir)/build_id/without main.c

with_debuglink:
	gcc -g -o hello main.c
	objcopy --only-keep-debug hello debug.dbg
	objcopy --strip-debug hello
	objcopy --add-gnu-debuglink=debug.dbg hello
