#!/bin/sh

# Gets the Unity version of a given executable, or searches for Unity
# executables within a directory. Pass it SteamApps/common/* to find every
# Unity game in your collection.

get_file_version()
{
	exe="$1"

	# Convert to windows path and escape \ ' characters
	win_name="$(cygpath -aw "$exe" | sed 's/\\/\\\\/g' | sed "s/'/\\\\'/g")"

	wmic datafile where name=\'"$win_name"\' get version | grep -v Version
}

is_unity_exe()
{
	exe="$1"

	[ -x "$exe" ] || return
	[ -f "$(basename "$exe" .exe)_data/Resources/unity default resources" ]
}

for arg in "$@"; do
	if [ -d "$arg" ]; then
		pushd "$arg" > /dev/null
			for file in *.exe; do
				is_unity_exe "$file" || continue

				version=$(get_file_version "$file")
				echo -e "$version\t$arg/$file"
			done
		popd > /dev/null
	else
		version=$(get_file_version "$arg")
		echo -e "$version\t$arg/$arg"
	fi
done
