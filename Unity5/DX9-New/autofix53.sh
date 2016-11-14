#!/bin/sh -e

DIR=~/3d-fixes
PATH="$DIR:$PATH"

EXTRACT=1
CLEANUP=1
UPDATE_INI=1

FIX_LIGHTING=1
FIX_HALO=1
FIX_REFLECTION=1

# If you need to force overwrite, add the option here:
LIGHTING_EXTRA=""

update_ini()
{
	if [ $UPDATE_INI -eq 1 ]; then
		cat | dos2unix | tee -a ../../DX9Settings.ini
	else
		cat > /dev/null
	fi
}

if [ $EXTRACT -eq 1 ]; then
	unity_asset_extractor.py *_Data/Resources/* *_Data/*.assets
	cd extracted
	extract_unity53_shaders.py */*.shader.decompressed --type=d3d9
	cd ShaderCRCs
fi

if [ $CLEANUP -eq 1 ]; then
	cleanup_unity_shaders.py ../..
fi

if [ $FIX_LIGHTING -eq 1 ]; then
	echo
	echo "Applying lighting fix..."
	find . \( -name 05F7E52C.txt \
	       -o -name 5D9CFDD4.txt \
	       -o -name 678DC18B.txt \
	       -o -name 2A3A109D.txt \
	       -o -name BB17C675.txt \
	       \) -a -print0 | xargs -0 dirname -z | sed -z 's/vp$/fp\/*.txt/' | xargs -0 \
			shadertool.py -I ../.. --fix-unity-lighting-ps-world --only-autofixed $LIGHTING_EXTRA | update_ini
	# TODO: Alternate lighting fix for directional lighting like DX11 template
fi

# TODO: Sun shafts

if [ $FIX_HALO -eq 1 ]; then
	echo
	echo "Applying vertex shader halo & reflection fixes..."
	# TODO: Frustum fix
	shadertool.py -I ../.. --fix-unity-reflection --auto-fix-vertex-halo --add-fog-on-sm3-update --only-autofixed --ignore-register-errors */vp/*.txt | update_ini
fi

if [ $FIX_REFLECTION -eq 1 ]; then
	echo "Applying pixel shader reflection fix..."
	shadertool.py -I ../.. --fix-unity-reflection --only-autofixed --ignore-register-errors */fp/*.txt | update_ini
fi
