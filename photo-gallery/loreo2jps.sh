#!/bin/sh

# Script to convert photos taken with the Loreo 9005 3D DSLR lens in a cap into
# .jps format. This script is not intended to be used alone - the .jps files
# should be cropped with my Stereo Photo Cropping Tool afterwards to adjust the
# parallax and/or crop off the overlap. By default this tool will copy 5%
# overlap from the center of the image to both eyes - the amount can be
# adjusted below, but keep in mind that since the divider between eyes is not
# in a fixed position on this lens (and there is no way to automatically
# determine what it was set to), you should be generous.

# OTOH for convenience you may want to set this negative to remove the overlap
# from both eyes, or 0 to just switch eyes... However, if you aren't going to
# do this properly you should probably not even bother swapping eyes and just
# leave the image as something that can be viewed with the distance method or
# leave it to the viewer to swap eyes - i.e. this is the wrong tool for you.

overlap=5

for file in "$@"; do
	base=$(basename "$file" .CR2)
	do_rm=0
	if [ "$base" != "$file" ]; then
		dcraw -e "$file"
		jpg="${base}.thumb.jpg"
		do_rm=1
	else
		base=$(basename "$file" .jpg)
		if [ "$base" = "$file" ]; then
			echo "Unknown file type"
			continue
		fi
		jpg="${file}"
	fi
	jps="${base}.jps"
	width=$(identify -format '%w' "$jpg")
	height=$(identify -format '%h' "$jpg")
	w2=$((($width / 2) + ($width * $overlap / 200)))
	x2=$((($width / 2) - ($width * $overlap / 200)))
	echo "$file -> $jps"
	convert "$jpg[${w2}x${height}+${x2}+0]" "$jpg[${w2}x${height}+0+0]" +append "$jps"
	if [ "$do_rm" -eq 1 ]; then
		rm "$jpg"
	fi
done
