#!/bin/sh

mkdir jps crosseyed distance mirrorl mirrorr anaglyph 2>/dev/null || true

for orig in "$@"; do
	[ ! -f "$orig" ] && continue
	base=$(basename "$orig" | sed 's/\.[^\.]*$//')
	echo "$orig"

	if echo "$orig" | grep -i '.mpo$' > /dev/null; then
		width=$(identify -format '%w' "$orig")
		rjpg=/tmp/$$_r.jpg
		ljpg=/tmp/$$_l.jpg
		exiftool $orig -o $ljpg
		exiftool $orig -mpimage2 -b > $rjpg
	else
		width=$(($(identify -format '%w' "$orig")/2))
		ljpg="$orig[${width}x${height}+${width}+0]"
		rjpg="$orig[${width}x${height}+0+0]"
	fi

	height=$(identify -format '%h' "$orig")
	white=$((width / 3))

	convert $rjpg $ljpg +append -quality 85% jps/${base}.jps
	convert $rjpg $ljpg -scale 25% +append crosseyed/${base}.jpg
	convert $ljpg $rjpg -scale 25% +append distance/${base}.jpg
	convert $ljpg -flop xc:white[${white}x${height}] $rjpg -scale 25% +append mirrorl/${base}.jpg
	convert $ljpg -flop xc:white[${white}x${height}] $rjpg -flop -scale 25% +append mirrorr/${base}.jpg

	r1jpg=/tmp/$$_r1.jpg
	l1jpg=/tmp/$$_l1.jpg

	convert $ljpg -scale 50% $l1jpg
	convert $rjpg -scale 50% $r1jpg
	composite $l1jpg $r1jpg -stereo +0 anaglyph/${base}.jpg

	rm $r1jpg $l1jpg

	if echo "$orig" | grep -i '.mpo$' > /dev/null; then
		rm $rjpg $ljpg
	fi
done

$(dirname $0)/mkindex.sh
