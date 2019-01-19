#!/bin/sh -e

DIR="$(readlink -f "$(dirname $0)/../..")"
. "$DIR/Unity5/DX9/checkenv.sh"

unity_asset_extractor.py *_Data/Resources/* *_Data/*.assets
cd extracted
extract_unity_shaders.py */*.shader --type=d3d9
cd ShaderCRCs

cleanup_unity_shaders.py ../..

# Lighting fix - match any shaders that use known lighting vertex shaders:
find . \( -name 05F7E52C.txt -o -name 678DC18B.txt \) -a -print0 | xargs -0 dirname -z | sed -z 's/vp$/fp\/*/' | xargs -0 \
	shadertool.py -I ../.. --fix-unity-lighting-ps --only-autofixed -f

# Vertex shader halo fix:
shadertool.py -I ../.. --auto-fix-vertex-halo --add-fog-on-sm3-update --only-autofixed --ignore-register-errors */vp/*.txt | unix2dos | tee -a ../../DX9Settings.ini
