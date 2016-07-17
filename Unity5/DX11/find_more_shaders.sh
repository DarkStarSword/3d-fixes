#!/bin/sh -e

DIR=~/3d-fixes
PATH="$DIR:$PATH"

if [ ! -f "d3d11.dll" ]; then
	echo "d3d11.dll not found - run this script from the game directory"
	exit 1
fi

if [ ! -d "extracted/ShaderFNVs" ]; then
	echo "You must first extract the shaders using unity_asset_extractor and extract_unity_shaders"
	exit 1
fi


echo ";;;;;;;;; LINES BELOW THIS POINT INSERTED BY FIND_MORE_SHADERS.PY ;;;;;;;;;;" | tee -a d3dx.ini

for x in extracted/ShaderFNVs/*/*vs.txt; do
	if [ -f "ShaderFixes/$(basename "$x" .txt)"_replace.txt -o -f "ShaderFixes/$x" ]; then
		# If it's already installed we skip it - hlsltool will
		# probably have already taken care of adding the sections for
		# these (FIME: there may be some with a halo fix that we could
		# use that won't have these sections)
		continue
	fi
	if grep "$(basename "$x" .txt)" d3dx.ini > /dev/null 6>&1; then
		continue
	fi
	if grep 'SHADOWCASTER' "$x" > /dev/null 2>&1; then
		# Shadow casters are drawn from the POV of a light, so their
		# matrices will give bad results if we try to use them.
		continue
	fi
	line0=$(head -n 1 "$x" | sed 's/^[^|]*|//')
	line1=$(sed -n 's/^\/\/\s*BindCB "UnityPerDraw" \([0-9]\+\)$/Resource_UnityPerDraw = vs-cb\1/p' "$x" | head -n 1)
	check1=$(sed -n 's/^\/\/\s*Matrix \([0-9]\+\) \[glstate_matrix_mvp\]$/GetMatrixFromReg = \1/p' "$x" | head -n 1)
	check2=$(sed -n 's/^\/\/\s*Matrix \([0-9]\+\) \[_Object2World\]\( 3\)\?$/GetMatrixFromReg1 = \1/p' "$x" | head -n 1)
	if [ -n "$line1" -a -n "$check1" -a -n "$check2" ]; then
		echo "[ShaderOverride_$(basename "$x" .txt)]" | tee -a d3dx.ini
		echo "hash = $(echo $(basename "$x") | sed 's/-.*//')" | tee -a d3dx.ini
		echo "; $line0" | tee -a d3dx.ini
		echo "$line1" | tee -a d3dx.ini
	fi
done
