#!/bin/sh -e

# This script is intended to run from cygwin or native Unix to ensure that the
# symbolically linked DLLs are correctly resolved in the zip file.

dir=$(readlink -f "$1")
tag="$2"
game=$(basename "$dir")
readme_src=README.md
readme_dst=3Dfix-README.txt
exclude="autofix.sh exclude devel_notes"
tmp_dir=$(dirname $(readlink -f "$0"))/__MKRELEASE_TMP__
rm_tmp_dir=

die()
{
	echo "$@"
	exit 1
}

if [ ! -d "$dir" -o ! "$tag" ]; then
	echo "Usage: $0 game tag"
	exit 1
fi

date="$3"
if [ -z "$date" ]; then
	date=$(date '+%Y-%m-%d')
fi

zip=${PWD}/3Dfix-${game}-$date.zip

if [ -f "$dir/d3dx.ini" ]; then
	echo Checking if d3dx.ini is in release mode...
	grep "hunting=1" "$dir/d3dx.ini" && die ABORTING: Hunting is enabled
	grep "hunting=2" "$dir/d3dx.ini" && die ABORTING: Hunting is enabled
	grep "calls=1" "$dir/d3dx.ini" && die ABORTING: Logging is enabled
	grep "input=1" "$dir/d3dx.ini" && die ABORTING: Logging is enabled
	grep "debug=1" "$dir/d3dx.ini" && die ABORTING: Logging is enabled
	grep "unbuffered=1" "$dir/d3dx.ini" && die ABORTING: Logging is unbuffered
	grep "convergence=1" "$dir/d3dx.ini" && die ABORTING: Logging is enabled
	grep "separation=1" "$dir/d3dx.ini" && die ABORTING: Logging is enabled
	grep "force_cpu_affinity=1" "$dir/d3dx.ini" && die ABORTING: CPU Affinity is being forced
	grep "export_fixed=1" "$dir/d3dx.ini" && die ABORTING: Dumping is enabled
	grep "export_shaders=1" "$dir/d3dx.ini" && die ABORTING: Dumping is enabled
	grep "export_hlsl=1" "$dir/d3dx.ini" && die ABORTING: Dumping is enabled
	grep "export_hlsl=2" "$dir/d3dx.ini" && die ABORTING: Dumping is enabled
	grep "export_hlsl=3" "$dir/d3dx.ini" && die ABORTING: Dumping is enabled
	grep "dump_usage=1" "$dir/d3dx.ini" && die ABORTING: Collecting usage statistics is enabled
	grep "waitfordebugger=1" "$dir/d3dx.ini" && die ABORTING: Wait for debugger is enabled
	grep "cache_shaders=0" "$dir/d3dx.ini" && die ABORTING: Shader cache is disabled
fi

if [ "$tag" != "--no-repo" ]; then
	status=$(git status --porcelain --ignored "$dir")
	if [ -n "$status" ]; then
		echo
		echo "ABORTING: Working directory is not clean!"
		git status -s "$dir" --ignored
		exit 1
	fi
fi

broken_symlinks=$(find -L "$dir" -type l -ls)
if [ -n "$broken_symlinks" ]; then
	echo
	echo "ABORTING: Broken symlinks found:"
	echo "$broken_symlinks"
	exit 1
fi

rm -fv "$zip" || true

need_tmp_dir=0
if [ -f "$dir/$readme_src" ]; then
	need_tmp_dir=1
else
	for excl in $exclude; do
		if [ -e "$dir/$excl" ]; then
			need_tmp_dir=1
			break
		fi
	done
fi

if [ $need_tmp_dir -eq 1 ]; then
	rm -frv "$tmp_dir"
	cp -as "$dir" "$tmp_dir"
	dir="$tmp_dir"
	rm_tmp_dir=1

	if [ -f "$dir/$readme_src" ]; then
		unix2dos -n "$dir/$readme_src" "$dir/$readme_dst"
		rm -f "$dir/$readme_src"
	fi

	for excl in $exclude; do
		if [ -e "$dir/$excl" ]; then
			rm -frv "$dir/$excl"
		fi
	done
fi

# Run in a subshell so that the current working directory is not changed in
# this shell. Do this instead of pushd/popd as those are *bash* builtins:
(
	if [ -d "$dir/zip" ]; then
		cd "$dir/zip" && zip -9 -r "$zip" . --exclude \*.swp
		if [ -f "$dir/$readme_dst" ]; then
			zip -9 -j "$zip" "$dir/$readme_dst"
		fi
	else
		cd "$dir" && zip -9 -r "$zip" . --exclude \*.swp
	fi
)

if [ "$rm_tmp_dir" = 1 ]; then
	rm -frv "$tmp_dir"
fi

if [ "$tag" != "--no-repo" ]; then
	echo
	git tag -f "$tag-$date" -m "$game $date"
	echo
	git show -s --format=short "$tag-$date"
fi
