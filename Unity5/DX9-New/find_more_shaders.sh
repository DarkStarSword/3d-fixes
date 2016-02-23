#!/bin/sh -e

DIR=~/3d-fixes
PATH="$DIR:$PATH"

if ! which shadertool.py > /dev/null 2>&1; then
	echo shadertool.py not found - adjust the DIR at the top of this script
	exit 1
fi

if [ ! -f "d3d9.dll" ]; then
	echo "d3d9.dll not found - run this script from the game directory"
	exit 1
fi

if [ ! -d "extracted/ShaderCRCs" ]; then
	echo "You must first extract the shaders using unity_asset_extractor and extract_unity_shaders"
	exit 1
fi

for x in extracted/ShaderCRCs/*/vp/*.txt; do
	if [ -f "ShaderOverride/VertexShaders/$(basename "$x")" ]; then
		# If it's already installed we skip it - shadertool will
		# probably have already taken care of adding the sections for
		# these (FIME: there may be some with a halo fix that we could
		# use that won't have these sections)
		continue
	fi
	if grep 'SHADOWCASTER' "$x" > /dev/null 2>&1; then
		# Shadow casters are drawn from the POV of a light, so their
		# matrices will give bad results if we try to use them.
		continue
	fi
	if grep '\<s0\>' "$x" > /dev/null 2>&1; then
		# Skip shaders that already use the default stereo sampler to
		# avoid Helix Mod clobbering it
		# FIXME: Check against DX9Settings.ini
		echo "$x" uses s0 - skipping
		continue
	fi
	line0=$(head -n 1 "$x" | sed 's/^[^|]*|//')
	line1=$(sed -n 's/^\/\/\s*Matrix \([0-9]\+\) \[glstate_matrix_mvp\]$/GetMatrixFromReg = \1/p' "$x" | head -n 1)
	line2=$(sed -n 's/^\/\/\s*Matrix \([0-9]\+\) \[_Object2World\]\( 3\)\?$/GetMatrixFromReg1 = \1/p' "$x" | head -n 1)
	if [ -n "$line1" -a -n "$line2" ]; then
		echo "[VS$(basename "$x" .txt)]" | tee -a DX9Settings.ini
		echo "; $line0" | tee -a DX9Settings.ini
		echo "$line1" | tee -a DX9Settings.ini
		echo "InverseMatrix = true" | tee -a DX9Settings.ini
		echo "$line2" | tee -a DX9Settings.ini
		shadertool.py -I . "$x"
	fi
done
