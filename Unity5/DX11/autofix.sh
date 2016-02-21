#!/bin/sh -e

DIR=~/3d-fixes
FXC=~/fxc.exe
PATH="$DIR:$PATH"

EXTRACT=1
UPDATE_INI=1

FIX_LIGHTING=1
FIX_SUN_SHAFTS=1
FIX_HALO=1

# If you need to force overwrite, add the option here:
LIGHTING_EXTRA=""

update_ini()
{
	if [ $UPDATE_INI -eq 1 ]; then
		cat | dos2unix | tee -a ../../d3dx.ini
	else
		cat > /dev/null
	fi
}

if [ $EXTRACT -eq 1 ]; then
	unity_asset_extractor.py *_Data/Resources/* *_Data/*.assets
	cd extracted
	extract_unity_shaders.py */*.shader --type=d3d11
	cd ShaderCRCs
fi

# TODO: DX11 version of:
# if [ $CLEANUP -eq 1 ]; then
# 	cleanup_unity_shaders.py ../..
# fi

if [ $FIX_LIGHTING -eq 1 ]; then
	# Lighting fix - match any shaders that use known lighting vertex shaders:
	find . \( -name 'b78925705424e647-vs*' -o -name 'ca5cfc8e4d8b1ce5-vs*' -o -name '69294277cca1bade-vs*' \) -a -print0 | xargs -0 dirname -z | sort -uz | sed -z 's/$/\/*-ps_replace.txt/' | xargs -0 \
		hlsltool.py -I ../.. --fix-unity-lighting-ps --only-autofixed --fxc "$FXC" $LIGHTING_EXTRA | update_ini
fi

if [ $FIX_SUN_SHAFTS -eq 1 ]; then
	hlsltool.py -I ../.. --fix-unity-sun-shafts --only-autofixed --fxc "$FXC" Hidden_SunShaftsComposite/*_replace.txt
fi

if [ $FIX_HALO -eq 1 ]; then
	# Vertex shader halo fix (TODO: vertex shader reflection fix):
	hlsltool.py -I ../.. --auto-fix-vertex-halo --only-autofixed --fxc "$FXC" */*vs_replace.txt
fi

# TODO: Pixel shader reflection fix
