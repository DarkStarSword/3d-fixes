#!/bin/sh

# This script is intended to run from cygwin or native Unix to ensure that the
# symbolically linked DLLs are correctly resolved in the zip file.

dir=$(readlink -f "$1")
game=$(basename "$dir")

if [ ! -d "$dir" ]; then
	echo "Usage: $0 game"
	exit 1
fi

cd "$dir" && zip -9 -r "../${game}.zip" .
