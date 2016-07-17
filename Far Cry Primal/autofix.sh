#!/bin/sh -e

DIR=~/3d-fixes
PATH="$DIR:$PATH"

asmtool.py -i --auto-fix-vertex-halo --only-autofixed ShaderCache/*-vs.txt
asmtool.py -i --fix-fcprimal-reflection --only-autofixed ShaderCache/*-ps.txt
asmtool.py -i --fix-fcprimal-physical-lighting --only-autofixed ShaderCache/*-cs.txt
# --fix-fcprimal-camera-pos improves a few subtle things, but must not be
# applied to vertex shaders. It's not clear that it's worth applying
# universally, so just adding it to wherever it makes a difference. The
# physical lighting fix implies it, so no need to do so explicitly there. Apply
# it to all shaders that include a cube map reflection:
asmtool.py -i --fix-fcprimal-camera-pos --only-autofixed $(grep -l ReflectionCubeTexture__TexObj__ ShaderCache/*-ps.txt)

# No - the light shaft shader in the cave near the start follows the same
# pattern and this would break it. There might be a unified pattern, but for
# now verify each as we find them.
######## Apply light position fix to volumetric fog shaders EXCEPT those that take a
######## shadow map as that would break light shafts (e.g. in the cave near the
######## beginning of the game):
#######asmtool.py -i --fix-fcprimal-light-pos --only-autofixed $(grep -L ShadowCmpSampler $(grep -l VFOutputBufferRGB ShaderCache/*-cs.txt))

echo Duplicate shaders:
ls ShaderFixes/*.txt | sed 's/_replace//' | sort | uniq -d
