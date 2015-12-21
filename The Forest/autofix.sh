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
	shadertool.py -I ../.. --stereo-sampler-vs=s3 --auto-fix-vertex-halo --fix-unity-reflection --add-fog-on-sm3-update --only-autofixed | unix2dos | tee -a ../../DX9Settings.ini

# Water halo fix in the pixel shader (with lessons learned from Stranded Deep -
# check vertex shaders to work out which texcoords to adjust and filter by keyword):
grep -lZ '^\/\/.*Keywords {.*SHADOWS_OFF' CetoTF_Ocean{Top,Under}Side_*/fp/*.txt | xargs -0 \
	shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection --adjust-unity-ceto-reflections --adjust-input=texcoord4 --adjust-input=texcoord5 --adjust-multiply=0.5 --ignore-other-errors | unix2dos | tee -a ../../DX9Settings.ini
grep -lZ '^\/\/.*Keywords {.*SHADOWS_SCREEN' CetoTF_Ocean{Top,Under}Side_*/fp/*.txt | xargs -0 \
	shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection --adjust-unity-ceto-reflections --adjust-input=texcoord4 --adjust-input=texcoord8 --adjust-multiply=0.5 --ignore-other-errors | unix2dos | tee -a ../../DX9Settings.ini
grep -lZ '^\/\/.*Keywords {.*SHADOWS_DEPTH' CetoTF_Ocean{Top,Under}Side_*/fp/*.txt | xargs -0 \
	shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection --adjust-unity-ceto-reflections --adjust-input=texcoord --ignore-other-errors | unix2dos | tee -a ../../DX9Settings.ini

# Reflection fix:
shadertool.py -I ../.. --stereo-sampler-ps=s15 --fix-unity-reflection --only-autofixed --ignore-register-errors */fp/*.txt | unix2dos | tee -a ../../DX9Settings.ini
