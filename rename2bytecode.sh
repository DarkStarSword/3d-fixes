#!/bin/sh

# Renames DX11 shaders to use their bytecode hash. Requires that the
# ShaderCache folder contains *all* replaced shaders dumped with their current
# hashes (e.g. 3DMigoto FNV) in *binary* form (use export_binary=1 hidden
# option in 3DMigoto). Run this script from the corresponding ShaderFixes
# folder.

DIR=$(dirname "$0")
PATH="$DIR:$PATH"

for shader_txt in ????????????????-*.txt; do
	shader_bin=$(echo "$shader_txt" | sed 's/\(................-.s\).*/\1.bin/')
	suffix=$(echo "$shader_txt" | sed 's/................\(-.s.*\)/\1/')

	orig_bin="../ShaderCache/$shader_bin"
	if [ ! -e "$orig_bin" ]; then
		echo "$orig_bin" not found
		continue
	fi

	new_hash=$(dx11shaderanalyse.py --bytecode-hash "$orig_bin" | \
		awk '/Bytecode hash/ {print $3}')

	new_file="00000000$new_hash$suffix"

	if [ -e "$new_file" ]; then
		echo
		diff -u "$new_file" "$shader_txt" | sed 's/^-/\x1b[41m-/;s/^+/\x1b[42m+/;s/^@/\x1b[34m@/;s/$/\x1b[0m/' | less -R
		echo "$shader_txt -> $new_file"
		mv -i "$shader_txt" "$new_file"
	else
		mv -vn "$shader_txt" "$new_file"
	fi
done
