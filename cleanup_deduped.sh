#!/bin/sh

if [ $(basename $(readlink -f .)) != FrameAnalysisDeduped ]; then
	echo Script must be run from a FrameAnalysisDeduped folder
	exit 1
fi

echo '================================================================================================='
echo '===                                                                                           ==='
echo '=== WARNING: About to delete all files in the current directory with only one hard link count ==='
echo '===                                                                                           ==='
echo '===                               Press enter to confirm                                      ==='
echo '===                                                                                           ==='
echo '================================================================================================='
read

for x in *; do
	if [ $(stat -c '%h' "$x") = '1' ]; then
		rm -v "$x"
	fi
done
