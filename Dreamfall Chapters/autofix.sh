#!/bin/sh -xe

DIR=~/3d-fixes

"$DIR/unity_asset_extractor.py" Dreamfall\ Chapters_Data/Resources/* Dreamfall\ Chapters_Data/*.assets
cd extracted
"$DIR/extract_unity_shaders.py" --vs-fog */*.shader --type=d3d9
cd ShaderCRCs

"$DIR/shadertool.py" -I ../.. --auto-fix-vertex-halo --only-autofixed */vp/*.txt
"$DIR/shadertool.py" -I ../.. --fix-unity-lighting-ps --only-autofixed Hidden_Internal-Deferred*/fp/* Hidden_Internal-PrePass*/fp/* Hidden_ShadowSoftener-*/fp/*
"$DIR/shadertool.py" -I ../.. --disable=0 Hidden_Coord/*/* Hidden_Depth/*/* Hidden_DepthBreaks/*/* Hidden_Final\ Interpolation/*/* Hidden_InterpolateAlongRays/*/* Hidden_Raymarch/*/*
