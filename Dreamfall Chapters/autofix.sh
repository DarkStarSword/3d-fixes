#!/bin/sh -xe

DIR=~/3d-fixes

"$DIR/unity_asset_extractor.py" Dreamfall\ Chapters_Data/Resources/* Dreamfall\ Chapters_Data/*.assets
cd extracted
"$DIR/extract_unity_shaders.py" */*.shader --type=d3d9
cd ShaderCRCs

# Order from most specific targets to least specific targets
"$DIR/shadertool.py" -I ../.. --disable=0 --condition=c200.x Hidden_Coord/*/* Hidden_Depth/*/* Hidden_DepthBreaks/*/* Hidden_Final\ Interpolation/*/* Hidden_InterpolateAlongRays/*/* Hidden_Raymarch/*/*
"$DIR/shadertool.py" -I ../.. --fix-unity-lighting-ps-world --only-autofixed Hidden_Internal-Deferred*/fp/* Hidden_Internal-PrePass*/fp/* Hidden_ShadowSoftener-*/fp/* >> ../../DX9Settings.ini
"$DIR/shadertool.py" -I ../.. --auto-fix-vertex-halo --fix-unity-reflection --add-fog-on-sm3-update --only-autofixed --ignore-register-errors */vp/*.txt >> ../../DX9Settings.ini
"$DIR/shadertool.py" -I ../.. --fix-unity-reflection --only-autofixed --ignore-register-errors */fp/*.txt >> ../../DX9Settings.ini
