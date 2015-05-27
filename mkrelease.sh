#!/bin/sh -e

# This script is intended to run from cygwin or native Unix to ensure that the
# symbolically linked DLLs are correctly resolved in the zip file.

dir=$(readlink -f "$1")
tag="$2"
game=$(basename "$dir")
readme_src=README.md
readme_dst=3Dfix-README.txt
tmp_dir=$(dirname $(readlink -f "$0"))/__MKRELEASE_TMP__
rm_tmp_dir=
date=$(date '+%Y-%m-%d')

if [ ! -d "$dir" -o ! "$tag" ]; then
	echo "Usage: $0 game tag"
	exit 1
fi

zip=${PWD}/3Dfix-${game}-$date.zip

status=$(git status --porcelain "$dir")
if [ -n "$status" ]; then
	echo
	echo "ABORTING: Working directory is not clean!"
	git status -s "$dir"
	exit 1
fi

broken_symlinks=$(find -L "$dir" -type l -ls)
if [ -n "$broken_symlinks" ]; then
	echo
	echo "ABORTING: Broken symlinks found:"
	echo "$broken_symlinks"
	exit 1
fi

rm -fv "$zip" || true

if [ -f "$dir/$readme_src" ]; then
	rm -frv "$tmp_dir"
	cp -as "$dir" "$tmp_dir"
	unix2dos -n "$tmp_dir/$readme_src" "$tmp_dir/$readme_dst"
	rm -f "$tmp_dir/$readme_src"
	dir="$tmp_dir"
	rm_tmp_dir=1

fi

# Run in a subshell so that the current working directory is not changed in
# this shell. Do this instead of pushd/popd as those are *bash* builtins:
(
	if [ -d "$dir/zip" ]; then
		cd "$dir/zip" && zip -9 -r "$zip" . --exclude \*.swp
		if [ -f "$dir/$readme_dst" ]; then
			zip -9 -j "$zip" "$dir/$readme_dst"
		fi
	else
		cd "$dir" && zip -9 -r "$zip" . --exclude \*.swp
	fi
)

if [ "$rm_tmp_dir" = 1 ]; then
	rm -frv "$tmp_dir"
fi

git tag -f "$tag-$date" -m "$game $date"
