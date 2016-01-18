#!/bin/sh -e

DIR=~/3d-fixes
PATH="$DIR:$PATH"

EXTRACT=1
CLEANUP=1
UPDATE_INI=1

FIX_LIGHTING=1
FIX_HALO=1
FIX_CETO=1
FIX_REFLECTION=1

OVERWRITE_CETO=0

if [ $OVERWRITE_CETO -eq 1 ]; then
	FORCE_CETO=--force
else
	FORCE_CETO=
fi

update_ini()
{
	if [ $UPDATE_INI -eq 1 ]; then
		cat | unix2dos | tee -a ../../DX9Settings.ini
	else
		cat > /dev/null
	fi
}

if [ $EXTRACT -eq 1 ]; then
	unity_asset_extractor.py *_Data/Resources/* *_Data/*.assets
	cd extracted
	extract_unity_shaders.py */*.shader --type=d3d9 --type=d3d11
	cd ShaderCRCs
fi

if [ $CLEANUP -eq 1 ]; then
	cleanup_unity_shaders.py ../..
fi

if [ $FIX_LIGHTING -eq 1 ]; then
	# Lighting fix - match any shaders that use known lighting vertex shaders:
	find . \( -name 05F7E52C.txt -o -name 678DC18B.txt \) -a -print0 | xargs -0 dirname -z | sed -z 's/vp$/fp\/*/' | xargs -0 \
		shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-lighting-ps-world --only-autofixed | update_ini
fi

if [ $FIX_HALO -eq 1 ]; then
	# Blacklist Ocean shaders as some of the vertex shaders do not have any free
	# sampler registers, so halos must be fixed in their pixel shaders instead
	find -maxdepth 1 -print0 | grep -zv '\(Ceto_OceanTopSide_\|Ceto_OceanUnderSide_\|Beam Team_Ocean_Ocean$\)' | sed -z 's/$/\/vp\/*/' | xargs -0 \
		shadertool.py -I ../.. --stereo-sampler-vs=s3 --fix-unity-reflection --auto-fix-vertex-halo --add-fog-on-sm3-update --only-autofixed --ignore-register-errors | update_ini
fi

if [ $FIX_CETO -eq 1 ]; then
	# Ocean halo fix in the pixel shader:
	# Not accurate when camera is tilted (don't want to spend too much time
	# on that given it's still Early Access, they keep changing the
	# shaders, and I'd like to replace this with a DX11 fix eventually)
	grep -lZ '^\/\/.*Keywords {.*DIRLIGHTMAP' Ceto_Ocean*Side_*/fp/*.txt | xargs -0 \
		shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection --adjust-input=texcoord4 --adjust-input=texcoord5 --adjust-multiply=0.5 --ignore-other-errors $FORCE_CETO | update_ini
	grep -lZ '^\/\/.*Keywords {.*SHADOWS_DEPTH' Ceto_Ocean*Side_*/fp/*.txt | xargs -0 \
		shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection --adjust-input=texcoord --ignore-other-errors $FORCE_CETO | update_ini
	# Ceto water has been updated - check the git history for fix for old versions with different shaders for point/spot lights
fi

# Old water system before Unity 5, no longer used AFAICT, but the shader is still present:
# shadertool.py -I ../.. --stereo-sampler-ps=s15 --adjust-input=v0 --adjust-input=v1 --adjust-multiply=0.5 Beam\ Team_Ocean_OceaB/fp/*

if [ $FIX_REFLECTION -eq 1 ]; then
	# Reflection fix:
	shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection --only-autofixed --ignore-register-errors */fp/*.txt | update_ini
fi
