#!/bin/sh

DIR=~/3d-fixes
PATH="$DIR:$PATH"

cs=$(ls *cs.txt)
ps=$(ls *ps.txt)

# Filter out all confetti physics compute shaders - these must have identical
# inputs and execute the same instructions on both eyes otherwise physics will
# desync:
cs=$(grep -L Confetti $cs)

# TODO: Add Screen Space Reflection fix here

# Sun/moon fog shaders - these need to be moved to infinity:
sun_moon_fog=$(grep -l FillVolumeTexture__VFOutputBuffer4 $cs)
cs=$(grep -L FillVolumeTexture__VFOutputBuffer4 $cs)
asmtool.py --fix-wd2-view-dir-reconstruction -i -f --only-autofixed $sun_moon_fog

# Fog fix alternate 1 (Adjusts all CS fog except sun/moon. Includes density):
fog_shaders=$(grep -l 'cbuffer VolumetricFog' $cs)
cs=$(grep -L 'cbuffer VolumetricFog' $cs)
asmtool.py --fix-wd2-volumetric-fog -i -f --only-autofixed $fog_shaders

# Fog fix alternate 2 (Adjusts all CS & PS fog except sun/moon and density. Seems less accurate in some cases?):
# asmtool.py --fix-wd2-unproject --fix-wd2-camera-pos --fix-wd2-view-dir-reconstruction --fix-wd2-camera-z-axis --fix-wd2-screen-space-reflections --fix-wd2-screen-space-reflections-cs -i -f --only-autofixed $cs

# Apply alternate 1 fog fix only to FV ("Fog Volume" as opposed to "Volumetric
# Fog" o_O ?) pixel shaders:
fv_shaders_ps=$(grep -l 'cbuffer FogVolumeRaymarch' $ps)
ps=$(grep -L 'cbuffer FogVolumeRaymarch' $ps)
asmtool.py --fix-wd2-volumetric-fog -i -f --only-autofixed $fv_shaders_ps

# Apply alternate 2 fog fix to *all* pixel shaders that mention fog (alternate
# 1 fix completely breaks windshield reflections, while this breaks some fog):
#fog_shaders_ps=$(grep -l 'cbuffer VolumetricFog' $ps)
#asmtool.py --fix-wd2-unproject --fix-wd2-camera-pos --fix-wd2-view-dir-reconstruction --fix-wd2-camera-z-axis --fix-wd2-screen-space-reflections --fix-wd2-screen-space-reflections-cs -i -f --only-autofixed $fog_shaders_ps


# Glass shaders use CameraPosition twice, but we only want to correct the first
# to fix reflections - the second will mess up sky reflections causing them to
# go out of bounds on the sky texture and show in only one eye.
glass_ps=$(grep -l 'cbuffer MaterialWD2Glass' $ps)
ps=$(grep -L 'cbuffer MaterialWD2Glass' $ps)
asmtool.py --fix-wd2-camera-pos-limit=1 -i -f --only-autofixed $glass_ps


# Lens grit shaders:
asmtool.py --fix-wd2-lens-grit=y2 -i -f --only-autofixed $(grep -l 'LensDirt' $ps)
ps=$(grep -L 'LensDirt' $ps)

# TODO: Add remaining fixes here
