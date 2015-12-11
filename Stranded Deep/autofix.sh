#!/bin/sh -e

DIR=~/3d-fixes
PATH="$DIR:$PATH"

unity_asset_extractor.py *_Data/Resources/* *_Data/*.assets
cd extracted
extract_unity_shaders.py */*.shader --type=d3d9 --type=d3d11
cd ShaderCRCs

cleanup_unity_shaders.py ../..

# Lighting fix - match any shaders that use known lighting vertex shaders:
find . \( -name 05F7E52C.txt -o -name 678DC18B.txt \) -a -print0 | xargs -0 dirname -z | sed -z 's/vp$/fp\/*/' | xargs -0 \
	shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-lighting-ps --only-autofixed # | unix2dos | tee -a ../../DX9Settings.ini

# Blacklist Ocean shaders as some of the vertex shaders do not have any free
# sampler registers, so halos must be fixed in their pixel shaders instead
find -maxdepth 1 -print0 | grep -zv '\(Ceto_OceanTopSide_BRDF\|Ceto_OceanUnderSide_BRDF\|Beam Team_Ocean_Ocean$\)' | sed -z 's/$/\/vp\/*/' | xargs -0 \
	shadertool.py -I ../.. --stereo-sampler-vs=s3 --auto-fix-vertex-halo --add-fog-on-sm3-update --only-autofixed | unix2dos | tee -a ../../DX9Settings.ini

# Ocean halo fix in the pixel shader:
shadertool.py -I ../.. --stereo-sampler-ps=s15 --adjust-input=texcoord5 --ignore-other-errors Ceto_OceanTopSide_BRDF/fp/*
shadertool.py -I ../.. --stereo-sampler-ps=s15 --adjust-input=texcoord4 --ignore-other-errors Ceto_OceanUnderSide_BRDF/fp/*
# shadertool.py -I ../.. --stereo-sampler-ps=s15 --adjust-input=v0 --adjust-input=v1 --adjust-multiply=0.5 Beam\ Team_Ocean_OceaB/fp/*

echo | unix2dos | tee -a ../../DX9Settings.ini
echo ';;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;' | unix2dos | tee -a ../../DX9Settings.ini
echo ';;;; Section added by script - Copy _ZBufferParams and _CameraDepthTexture ;;;;' | unix2dos | tee -a ../../DX9Settings.ini

for x in Ceto_OceanTopSide_BRDF/fp/* Ceto_OceanUnderSide_BRDF/fp/* Beam\ Team_Ocean_Ocean/fp/*; do
	line0=$(head -n 1 "$x" | sed 's/^[^|]*|//')
	line1=$(sed -n 's/^\/\/\s*Vector \([0-9]\+\) \[_ZBufferParams\]$/GetConst1FromReg = \1/p' "$x")
	line2=$(sed -n 's/^\/\/\s*SetTexture \([0-9]\+\) \[_CameraDepthTexture\] 2D \1$/GetSampler1FromReg = \1/p' "$x")
	if [ -n "$line1" -a -n "$line2" ]; then
		echo "[PS$(basename "$x" .txt)]" | unix2dos | tee -a ../../DX9Settings.ini
		echo ";$line0" | unix2dos | tee -a ../../DX9Settings.ini
		echo "$line1" | unix2dos | tee -a ../../DX9Settings.ini
		echo "$line2" | unix2dos | tee -a ../../DX9Settings.ini
	fi
done

echo ';;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;' | unix2dos | tee -a ../../DX9Settings.ini

echo
echo Now go remove any duplicate sections in the DX9Settings.ini!
