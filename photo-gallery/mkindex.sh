#!/bin/sh

output_head()
{
	echo "<html><head><title>$@</title></head><body>"
}

output_footer()
{
	echo '</body></html>'
}

output_img()
{
	src="$1"
	style="$2"
	echo "<img style='$style' src='$src' />"
}

output_viewing_methods_2()
{
	target="$1"

	echo "<a href='../crosseyed/$target'>Crosseyed</a>"
	echo "<a href='../distance/$target'>Distance</a>"
	echo "<a href='../mirrorl/$target'>Mirror Left</a>"
	echo "<a href='../mirrorr/$target'>Mirror Right</a>"
	echo "<a href='../anaglyph/$target'>Anaglyph</a>"
}

output_viewing_methods()
{
	target="$1"
	originals="$2"

	echo "<p>Change viewing method: "
	originals="$2"

	if [ "$originals" = 1 ]; then
		echo "<a href='../originals'>Originals</a>"
	fi
	echo "<a href='../jps/$target'>Full Size JPS</a>"
	output_viewing_methods_2 "$target"
	echo "</p>"
}

generate_index()
(
	folder="$1"
	style="$2"
	title="$3"

	(
		cd "$folder"
		output_head "$title" > index.html
		echo "<p><a href="../..">Back to gallaries</a>" >> index.html
		output_viewing_methods "" 1 >> index.html
		for file in *.jpg *.JPG *.jps *.JPS *.mpo *.MPO; do
			[ ! -f "$file" ] && continue

			html=$(basename "$file" | sed 's/\.[^\.]*$//').html
			output_head "$title - $file" > $html
			echo "<p><a href=".">Back to index</a></p>" >> $html
			output_viewing_methods "$html" 0 >> $html
			echo "<p><a href='$file'>" >> $html
			echo "$(output_img "$file" "$style")" >> $html
			echo "</a></p>" >> $html
			output_footer >> $html

			embed=$(basename "$file" | sed 's/\.[^\.]*$//')-embed.html
			output_head "$title - $file" > $embed
			echo "<a href='$html' target='_parent'>" >> $embed
			echo "$(output_img "$file" "width: 100%;")" >> $embed
			echo "</a><br />" >> $embed
			output_viewing_methods_2 "$embed" 0 >> $embed
			output_footer >> $embed

			echo "<p><a href='$html'>$(output_img "$file" "$style")</a></p>" >> index.html
		done
		output_footer >> index.html
	)
)

# generate_index originals "100%" "Stereo Photos - Originals"
generate_index jps "width: 100%;" "Stereo Photos - Full Size JPS"
generate_index crosseyed "width: 25cm;" "Stereo Photos - Crosseyed Viewing Method"
generate_index distance "width: 20cm;" "Stereo Photos - Distance Viewing Method"
generate_index mirrorl "width: 100%;" "Stereo Photos - Mirror Left Viewing Method"
generate_index mirrorr "width: 100%;" "Stereo Photos - Mirror Right Viewing Method"
generate_index anaglyph "width: 100%;" "Stereo Photos - Red/Cyan Anaglyph Viewing Method"
