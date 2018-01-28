#!/bin/sh -e

# This script is intended to run from cygwin or native Unix to ensure that the
# symbolically linked DLLs are correctly resolved in the zip file.

compression="zip"
dir=
tag=
version=
readme_src=README.md
readme_dst=3Dfix-README.txt
exclude="autofix.sh exclude devel_notes .git"
tmp_dir=$(dirname $(readlink -f "$0"))/__MKRELEASE_TMP__
rm_tmp_dir=

for arg in "$@"; do
	case "$arg" in
		"--no-repo")
			if [ -n "$tag" ]; then
				echo "--no-repo must be specified earlier on the commane line"
				exit 1
			fi
			tag="--no-repo"
			;;

		"--7z")
			compression="7z"
			;;

		*)
			if [ -z "$dir" ]; then
				dir=$(readlink -f "$arg")
			elif [ -z "$tag" ]; then
				tag="$arg"
			elif [ -z "$version" ]; then
				version="$arg"
			else
				echo "Unexpected argument: $arg"
				exit 1
			fi
			;;
	esac
done

die()
{
	echo "$@"
	exit 1
}

if [ ! -d "$dir" -o ! "$tag" ]; then
	die "Usage: $0 game ( tag | --no-repo ) [ version ]"
fi

game=$(basename "$dir")

if [ -z "$version" ]; then
	version=$(date '+%Y-%m-%d')
fi

archive="${PWD}/3Dfix-${game}-${version}"

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
	grep "export_binary=1" "$dir/d3dx.ini" && die ABORTING: Dumping is enabled
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

rm -fv "${archive}.${compression}" || true

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
	echo "Symlinking files to a temporary directory..."
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

compress_archive()
{
	echo "Creating ${archive}.${compression}"

	if [ "$compression" = "zip" ]; then
		zip -9 -r "${archive}.zip" . --exclude \*.swp
	elif [ "$compression" = "7z" ]; then
		7z a -l -t7z -m0=lzma -mx=9 -mfb=64 -md=32m -ms=on "${archive}.7z" .
	else
		die "Bug: Unsupported compression $compression"
	fi
}

add_readme_to_archive()
{
	if [ "$compression" = "zip" ]; then
		zip -9 -j "${archive}.zip" "$dir/$readme_dst"
	elif [ "$compression" = "7z" ]; then
		7z a -l -t7z -m0=lzma -mx=9 -mfb=64 -md=32m -ms=on "${archive}.7z" "$dir/$readme_dst"
	else
		die "Bug: Unsupported compression $compression"
	fi
}

# Run in a subshell so that the current working directory is not changed in
# this shell. Do this instead of pushd/popd as those are *bash* builtins:
(
	if [ -d "$dir/zip" ]; then
		cd "$dir/zip" && compress_archive
		if [ -f "$dir/$readme_dst" ]; then
			add_readme_to_archive
		fi
	else
		cd "$dir" && compress_archive
	fi
)

if [ "$rm_tmp_dir" = 1 ]; then
	rm -frv "$tmp_dir"
fi

if [ "$tag" != "--no-repo" ]; then
	echo
	git tag -f "$tag-$version" -m "$game $version"
	echo
	git show -s --format=short "$tag-$version"
fi
