#!/bin/sh

DIR=~/3d-fixes
PATH="$DIR:$PATH"

shadertool.py -i --stereo-sampler-ps=s15 --disable-redundant-unreal-correction --auto-fix-unreal-shadows --auto-fix-unreal-lights --auto-fix-unreal-dne-reflection --only-autofixed --quiet Dumps/AllShaders/PixelShader/*.txt
mkdir processed
mv -v Dumps/AllShaders/PixelShader/*.txt processed/
