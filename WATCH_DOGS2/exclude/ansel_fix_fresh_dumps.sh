#!/bin/sh

DIR=~/3d-fixes
AUTOFIX="$DIR/WATCH_DOGS2/autofix.sh"

all_bin=$(ls *.bin)
all_asm=$(ls *s.txt)
bin_as_asm=$(echo $all_bin | sed 's/bin/txt/g')
new=$(echo $all_asm $all_asm $bin_as_asm | sed 's/ /\n/g' | sort | uniq -u)
new_bin=$(echo $new | sed 's/txt/bin/g')

for bin in $new_bin; do
	tmp=$(echo "$bin" | sed 's/bin/asm/')
	asm=$(echo "$bin" | sed 's/bin/txt/')
	chmod 644 "$bin"
	~/3d-fixes/cmd_Decompiler -d "$bin"
	mv "$tmp" "$asm"
	chmod 644 $asm

	"$AUTOFIX" "$asm"
done
