#!/bin/sh -xe

DIR=~/3d-fixes
PATH="$DIR:$PATH"

unity_asset_extractor.py Dreamfall\ Chapters_Data/Resources/* Dreamfall\ Chapters_Data/*.assets
cd extracted
extract_unity53_shaders.py */*.shader.decompressed --type=d3d9
cd ShaderCRCs

cleanup_unity_shaders.py ../..

# Order from most specific targets to least specific targets
shadertool.py -I ../.. --disable=0 --condition=c200.x Hidden_Coord/*/*.txt Hidden_Depth/*/*.txt Hidden_DepthBreaks/*/*.txt Hidden_Final\ Interpolation/*/*.txt Hidden_InterpolateAlongRays/*/*.txt Hidden_Raymarch/*/*.txt
shadertool.py -I ../.. --fix-unity-lighting-ps-world --only-autofixed Hidden_Internal-Deferred*/fp/*.txt Hidden_Internal-PrePass*/fp/*.txt Hidden_ShadowSoftener-*/fp/*.txt | unix2dos | tee -a ../../DX9Settings.ini
shadertool.py -I ../.. --auto-fix-vertex-halo --fix-unity-reflection --add-fog-on-sm3-update --only-autofixed --ignore-register-errors */vp/*.txt | unix2dos | tee -a ../../DX9Settings.ini
shadertool.py -I ../.. --fix-unity-reflection --only-autofixed --ignore-register-errors */fp/*.txt | unix2dos | tee -a ../../DX9Settings.ini
