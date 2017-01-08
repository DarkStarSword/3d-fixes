#!/bin/sh

DIR=~/3d-fixes
PATH="$DIR:$PATH"

if [ $# -eq 0 ]; then
	asm_shaders=$(ls *s.txt)
else
	asm_shaders="$@"
fi

cs=$(echo $asm_shaders | sed 's/ /\n/g' | grep cs.txt)
ps=$(echo $asm_shaders | sed 's/ /\n/g' | grep ps.txt)
vs=$(echo $asm_shaders | sed 's/ /\n/g' | grep vs.txt)

autofix_cs()
{
	# Filter out all confetti physics compute shaders - these must have identical
	# inputs and execute the same instructions on both eyes otherwise physics will
	# desync:
	cs=$(grep -L Confetti $cs)
	[ -z "$cs" ] && return

	# Ocean screen space reflection shaders:
	xx=$(grep -l SSPRWMirrorViewProjMatrix $cs)
	cs=$(grep -L SSPRWMirrorViewProjMatrix $cs)
	[ -n "$xx" ] && asmtool.py --fix-wd2-screen-space-reflections-cs -i -f --only-autofixed $xx
	[ -z "$cs" ] && return

	# Sun/moon fog shaders - these need to be moved to infinity:
	xx=$(grep -l FillVolumeTexture__VFOutputBuffer4 $cs)
	cs=$(grep -L FillVolumeTexture__VFOutputBuffer4 $cs)
	[ -n "$xx" ] && asmtool.py --fix-wd2-view-dir-reconstruction -i -f --only-autofixed $xx
	[ -z "$cs" ] && return

	# Fog fix alternate 1 (Adjusts all CS fog except sun/moon. Includes density):
	xx=$(grep -l 'cbuffer VolumetricFog' $cs)
	cs=$(grep -L 'cbuffer VolumetricFog' $cs)
	[ -n "$xx" ] && asmtool.py --fix-wd2-volumetric-fog -i -f --only-autofixed $xx
	[ -z "$cs" ] && return

	# Fog fix alternate 2 (Adjusts all CS & PS fog except sun/moon and density. Seems less accurate in some cases?):
	# asmtool.py --fix-wd2-unproject --fix-wd2-camera-pos --fix-wd2-view-dir-reconstruction --fix-wd2-camera-z-axis=1 --fix-wd2-screen-space-reflections --fix-wd2-screen-space-reflections-cs -i -f --only-autofixed $cs
	# [ -z "$cs" ] && return
}

autofix_ps()
{
	# Screen space reflections (except Ocean):
	xx=$(grep -l 'cbuffer SSR' $ps)
	ps=$(grep -L 'cbuffer SSR' $ps)
	[ -n "$xx" ] && asmtool.py --fix-wd2-screen-space-reflections -i -f --only-autofixed $xx
	[ -z "$ps" ] && return

	# Apply fog fix only to FV ("Fog Volume" as opposed to "Volumetric Fog" o_O ?)
	# pixel shaders:
	xx=$(grep -l 'cbuffer FogVolumeRaymarch' $ps)
	ps=$(grep -L 'cbuffer FogVolumeRaymarch' $ps)
	# Alternate 1 only fixes fog, not sun/moon glow:
	#[ -n "$xx" ] && asmtool.py --fix-wd2-volumetric-fog -i -f --only-autofixed $xx
	# Alternate 3 fixes fog AND sun/moon glow (the sun can still catch incorrectly on objects, this only fixes the sky):
	[ -n "$xx" ] && asmtool.py --fix-wd2-camera-pos --fix-wd2-camera-z-axis=-1 -i -f --only-autofixed $xx
	[ -z "$ps" ] && return

	# Glass shaders use CameraPosition twice, but we only want to correct the first
	# to fix reflections - the second will mess up sky reflections causing them to
	# go out of bounds on the sky texture and show in only one eye.
	xx=$(grep -l 'cbuffer MaterialWD2Glass' $ps)
	ps=$(grep -L 'cbuffer MaterialWD2Glass' $ps)
	[ -n "$xx" ] && asmtool.py --fix-wd2-camera-pos-limit=1 -i -f --only-autofixed $xx
	[ -z "$ps" ] && return

	# Similar problem with some of the hair shaders - adjusting the second camera
	# position causes the reflections to go out of whack, so limit to the first (a
	# lot only use one - they are fine):
	xx=$(grep -l 'cbuffer MaterialWD2Hair' $ps)
	ps=$(grep -L 'cbuffer MaterialWD2Hair' $ps)
	[ -n "$xx" ] && asmtool.py --fix-wd2-camera-pos-limit=1 -i -f --only-autofixed $xx
	[ -z "$ps" ] && return

	# Lens grit shaders:
	xx=$(grep -l 'LensDirt' $ps)
	ps=$(grep -L 'LensDirt' $ps)
	[ -n "$xx" ] && asmtool.py --fix-wd2-lens-grit=y2 -i -f --only-autofixed $xx
	[ -z "$ps" ] && return

	# Fix for uniform fog that sometimes blanket the City at night. These shaders
	# are Ansel exclusive and can accept a projection offset parameter - they are
	# designed to work in stereo to work with Ansel. Moves the fog to the correct
	# depth in Ansel. By itself this creates cube artefacts in the sky, which needs
	# to be corrected in the vertex shader (6aecd428560649f8).
	xx=$(grep -l 'VFProjectionOffset.*[0-9]$' $ps)
	ps=$(grep -L 'VFProjectionOffset.*[0-9]$' $ps)
	[ -n "$xx" ] && asmtool.py --fix-wd2-camera-pos --fix-wd2-view-dir-reconstruction -i -f --only-autofixed $xx
	[ -z "$ps" ] && return
	# Based on the shaders that take a VFProjectionOffset in Ansel, we notice they
	# write to a UAV and we might be able to assume that other pixel shaders that
	# write to the same UAV might require the same pattern. Two of the shaders
	# matched in the above pattern write to GIFillLightFog__VFLightOutputBuffer,
	# and the third writes to FogVolumes__VFOutputBuffer1:
	xx=$(grep -l 'GIFillLightFog__VFLightOutputBuffer' $ps)
	ps=$(grep -L 'GIFillLightFog__VFLightOutputBuffer' $ps)
	[ -n "$xx" ] && asmtool.py --fix-wd2-camera-pos --fix-wd2-view-dir-reconstruction -i -f --only-autofixed $xx
	[ -z "$ps" ] && return
	# FogVolumes__VFOutputBuffer1 shaders had no visible change (not saying they don't, just not in the current weather):
	xx=$(grep -l 'FogVolumes__VFOutputBuffer1' $ps)
	ps=$(grep -L 'FogVolumes__VFOutputBuffer1' $ps)
	[ -n "$xx" ] && asmtool.py --fix-wd2-camera-pos --fix-wd2-view-dir-reconstruction -i -f --only-autofixed $xx
	[ -z "$ps" ] && return

	# Apply alternate 2 fog fix to *all* pixel shaders that mention fog (alternate
	# 1 fix completely breaks windshield reflections, while this breaks some fog):
	#xx=$(grep -l 'cbuffer VolumetricFog' $ps)
	#[ -n "$xx" ] && asmtool.py --fix-wd2-unproject --fix-wd2-camera-pos --fix-wd2-view-dir-reconstruction --fix-wd2-camera-z-axis=1 --fix-wd2-screen-space-reflections --fix-wd2-screen-space-reflections-cs -i -f --only-autofixed $xx

	# Reflections, shadows, etc. Do not force overwrite these as some shaders are
	# blacklisted. Should be done last:
	[ -n "$ps" ] && asmtool.py --fix-wd2-unproject --fix-wd2-camera-pos -i --only-autofixed $ps
	return
}

autofix_vs()
{
	# Move fake interior lights to correct depth:
	xx=$(grep -l '//   float4 FakeInteriorTextureSize;    // Offset:   32 Size:    16$' $vs)
	vs=$(grep -L '//   float4 FakeInteriorTextureSize;    // Offset:   32 Size:    16$' $vs)
	[ -n "$xx" ] && asmtool.py --fix-wd2-camera-pos-excluding=1 -i -f --only-autofixed $xx
	[ -z "$vs" ] && return

	# Fix halo issues on water. Commented out because these also require a
	# driver neutralisation to fix the reflections if the pattern applies,
	# which isn't scripted in asmtool yet.
	# xx=$(grep -l 'cbuffer (MaterialWD2Water|WaterGrid)' $vs)
	# vs=$(grep -L 'cbuffer (MaterialWD2Water|WaterGrid)' $vs)
	# [ -n "$xx" ] && asmtool.py --auto-fix-vertex-halo -i --only-autofixed $xx
	# [ -z "$vs" ] && return

	# Fix uneven lighting on steam and other effects that consider volumetric fog:
	xx=$(grep -l 'VolumetricFog__VFLightVolumeTexture__TexObj__' $vs)
	vs=$(grep -L 'VolumetricFog__VFLightVolumeTexture__TexObj__' $vs)
	[ -n "$xx" ] && asmtool.py --auto-fix-vertex-halo -i --only-autofixed $xx
	[ -z "$vs" ] && return
}

[ -n "$cs" ] && autofix_cs
[ -n "$ps" ] && autofix_ps
[ -n "$vs" ] && autofix_vs
