#!/bin/sh -e

DIR=~/3d-fixes
PATH="$DIR:$PATH"

asmtool.py -i --auto-fix-vertex-halo --only-autofixed ShaderCache/*-vs.txt
asmtool.py -i --fix-fcprimal-reflection --only-autofixed ShaderCache/*-ps.txt
asmtool.py -i --fix-fcprimal-physical-lighting --only-autofixed ShaderCache/*-cs.txt
# --fix-fcprimal-camera-pos improves a few subtle things, but must not be
# applied to vertex shaders. It's not clear that it's worth applying
# universally, so just adding it to wherever it makes a difference. The
# physical lighting fix implies it.
