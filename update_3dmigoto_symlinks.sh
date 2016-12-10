#!/bin/sh

path=$(dirname "$0")
script=$(basename "$0")
if [ -z "$1" ]; then
	migoto=$(find "$path" -maxdepth 1 -type d -iname "3Dmigoto-*.*.*" -printf '%f\n' | sort --version-sort -r | head -n 1)
else
	migoto="3Dmigoto-$1"
fi

echo "Updating to $migoto..."
find . -lname '*/3Dmigoto-*.*.*' -print0 |
	while IFS= read -r -d $'\0' link; do
		newtarget=$(readlink "$link" | sed "s/3Dmigoto-[0-9]\+\.[0-9]\+\.[0-9]\+/$migoto/g")
		ln -sfv "$newtarget" "$link"
		git add "$link"
	done

gamedir="$(basename "$PWD")"
if [ "$gamedir" = "3d-fixes" ]; then
	gamedir="Global"
fi
git commit -m "$gamedir: Update to $migoto

Symbolic links updated via $script" -e
