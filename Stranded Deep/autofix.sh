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
	shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-lighting-ps-world --only-autofixed | unix2dos | tee -a ../../DX9Settings.ini

# Blacklist Ocean shaders as some of the vertex shaders do not have any free
# sampler registers, so halos must be fixed in their pixel shaders instead
find -maxdepth 1 -print0 | grep -zv '\(Ceto_OceanTopSide_BRDF\|Ceto_OceanUnderSide_BRDF\|Beam Team_Ocean_Ocean$\)' | sed -z 's/$/\/vp\/*/' | xargs -0 \
	shadertool.py -I ../.. --stereo-sampler-vs=s3 --fix-unity-reflection --auto-fix-vertex-halo --add-fog-on-sm3-update --only-autofixed --ignore-register-errors | unix2dos | tee -a ../../DX9Settings.ini

# Ocean halo fix in the pixel shader:
grep -lZ '^\/\/.*Keywords {.*\(DIRECTIONAL\|POINT\|SPOT\)' Ceto_OceanTopSide_BRDF/fp/*.txt | xargs -0 grep -LZ '^\/\/.*Keywords {.*DIRLIGHTMAP' | xargs -0 \
	shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection --adjust-input=texcoord5 --adjust-input=texcoord6 --ignore-other-errors #| unix2dos | tee -a ../../DX9Settings.ini
grep -lZ '^\/\/.*Keywords {.*DIRLIGHTMAP' Ceto_OceanTopSide_BRDF/fp/*.txt | xargs -0 \
	shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection --adjust-input=texcoord5 --ignore-other-errors #| unix2dos | tee -a ../../DX9Settings.ini

grep -lZ '^\/\/.*Keywords {.*\(DIRECTIONAL\|POINT\|SPOT\)' Ceto_OceanUnderSide_BRDF/fp/*.txt | xargs -0 grep -LZ '^\/\/.*Keywords {.*DIRLIGHTMAP' | xargs -0 \
	shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection --adjust-input=texcoord5 --ignore-other-errors #| unix2dos | tee -a ../../DX9Settings.ini
grep -lZ '^\/\/.*Keywords {.*DIRLIGHTMAP' Ceto_OceanUnderSide_BRDF/fp/*.txt | xargs -0 \
	shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection --adjust-input=texcoord4 --ignore-other-errors #| unix2dos | tee -a ../../DX9Settings.ini
grep -lZ '^\/\/.*Keywords {.*SHADOWS_DEPTH' Ceto_OceanUnderSide_BRDF/fp/*.txt | xargs -0 \
	shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection --adjust-input=texcoord --ignore-other-errors #| unix2dos | tee -a ../../DX9Settings.ini

# shadertool.py -I ../.. --stereo-sampler-ps=s15 --adjust-input=v0 --adjust-input=v1 --adjust-multiply=0.5 Beam\ Team_Ocean_OceaB/fp/*

# Reflection fix:
shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection --only-autofixed --ignore-register-errors */fp/*.txt | unix2dos | tee -a ../../DX9Settings.ini
