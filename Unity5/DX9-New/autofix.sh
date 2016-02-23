#!/bin/sh -e

DIR=~/3d-fixes
PATH="$DIR:$PATH"

unity_asset_extractor.py *_Data/Resources/* *_Data/*.assets
cd extracted
extract_unity_shaders.py */*.shader --type=d3d9
cd ShaderCRCs

cleanup_unity_shaders.py ../..

# Lighting fix - match any shaders that use known lighting vertex shaders:
find . \( -name 05F7E52C.txt -o -name 678DC18B.txt \) -a -print0 | xargs -0 dirname -z | sed -z 's/vp$/fp\/*/' | xargs -0 \
	shadertool.py -I ../.. --fix-unity-lighting-ps-world --only-autofixed | unix2dos | tee -a ../../DX9Settings.ini

# Vertex shader halo and reflection fix:
shadertool.py -I ../.. --fix-unity-reflection --auto-fix-vertex-halo --add-fog-on-sm3-update --only-autofixed --ignore-register-errors */vp/*.txt | unix2dos | tee -a ../../DX9Settings.ini

# Pixel shader reflection fix:
shadertool.py -I ../.. --fix-unity-reflection --only-autofixed --ignore-register-errors */fp/*.txt | unix2dos | tee -a ../../DX9Settings.ini
