#!/bin/sh -e

DIR=~/3d-fixes
PATH="$DIR:$PATH"

unity_asset_extractor.py *_data/Resources/* *_data/*.assets
cd extracted
extract_unity_shaders.py */*.shader --type=d3d9
cd ShaderCRCs

cleanup_unity_shaders.py ../..

# Lighting fix - match any shaders that use known lighting vertex shaders:
find . \( -name 05F7E52C.txt -o -name 678DC18B.txt \) -a -print0 | xargs -0 dirname -z | sed -z 's/vp$/fp\/*/' | xargs -0 \
	shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-lighting-ps-world --only-autofixed | unix2dos | tee -a ../../DX9Settings.ini

# Blacklist Ocean shaders as some of the vertex shaders do not have any free
# sampler registers, so halos must be fixed in their pixel shaders instead
find -maxdepth 1 -print0 | grep -zv '\(CetoTF_OceanTopSide\|CetoTF_OceanUnderSide\|Ceto_OceanMask\)' | sed -z 's/$/\/vp\/*/' | xargs -0 \
	shadertool.py -I ../.. --auto-fix-vertex-halo --fix-unity-reflection --add-fog-on-sm3-update --only-autofixed | unix2dos | tee -a ../../DX9Settings.ini

# Water halo fix in the pixel shader:
shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection  --adjust-input=texcoord4 --adjust-input=texcoord5 --adjust-multiply=0.5 --ignore-other-errors CetoTF_OceanTopSide*/fp/* | unix2dos | tee -a ../../DX9Settings.ini
shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection  --adjust-input=texcoord4 --adjust-input=texcoord5 --adjust-multiply=0.5 --ignore-other-errors CetoTF_OceanUnderSide*/fp/* | unix2dos | tee -a ../../DX9Settings.ini

# Reflection fix:
shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection --only-autofixed --ignore-register-errors */fp/*.txt | unix2dos | tee -a ../../DX9Settings.ini
