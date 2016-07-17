#!/bin/sh

# Renames DX11 shaders to use their embedded hash. Requires that the
# ShaderCache folder contains *all* replaced shaders dumped with their current
# hashes (e.g. 3DMigoto FNV) in *binary* form (use export_binary=1 hidden
# option in 3DMigoto). Run this script from the corresponding ShaderFixes
# folder.

DIR=$(dirname "$0")
PATH="$DIR:$PATH"

for shader_txt in *.txt; do
	shader_bin=$(echo "$shader_txt" | sed 's/\(................-.s\).*/\1.bin/')
	suffix=$(echo "$shader_txt" | sed 's/................\(-.s.*\)/\1/')

	orig_bin="../ShaderCache/$shader_bin"
	if [ ! -e "$orig_bin" ]; then
		echo "$orig_bin" not found
		continue
	fi

	new_hash=$(dx11shaderanalyse.py -v "$orig_bin" | \
		awk '/Embedded hash/ {print $3}' | sed 's/^\(................\).*/\1/')

	mv -v "$shader_txt" "$new_hash$suffix"
done
