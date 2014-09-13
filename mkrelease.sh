#!/bin/sh -e

# This script is intended to run from cygwin or native Unix to ensure that the
# symbolically linked DLLs are correctly resolved in the zip file.

dir=$(readlink -f "$1")
game=$(basename "$dir")
readme_src=README.md
readme_dst=3Dfix-README.txt
tmp_dir=$(dirname $(readlink -f "$0"))/__MKRELEASE_TMP__
rm_tmp_dir=

if [ ! -d "$dir" ]; then
	echo "Usage: $0 game"
	exit 1
fi

zip=${PWD}/3Dfix-${game}-$(date '+%Y-%m-%d').zip

rm -fv "$zip" || true

if [ -f "$dir/$readme_src" ]; then
	rm -frv "$tmp_dir"
	cp -as "$dir" "$tmp_dir"
	mv "$tmp_dir/$readme_src" "$tmp_dir/$readme_dst"
	dir="$tmp_dir"
	rm_tmp_dir=1

fi

cd "$dir" && zip -9 -r "$zip" .

if [ "$rm_tmp_dir" = 1 ]; then
	rm -frv "$tmp_dir"
fi
