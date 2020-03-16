#!/bin/sh -e

echo NOTE: This particular autofix variant is untested

DIR="$(readlink -f "$(dirname $0)/../..")"
. "$DIR/Unity5/DX9/checkenv.sh"

# You can now pass these options in via environment variables, like:
# EXTRACT=0 ~/3d-fixes/Unity5/DX9-New/autofix55.sh
[ -z "$EXTRACT" ]        && EXTRACT=1
[ -z "$CLEANUP" ]        && CLEANUP=1
[ -z "$COPY_TEMPLATE" ]  && COPY_TEMPLATE=1
[ -z "$UPDATE_INI" ]     && UPDATE_INI=1

[ -z "$FIX_LIGHTING" ]   && FIX_LIGHTING=1
[ -z "$FIX_SUN_SHAFTS" ] && FIX_SUN_SHAFTS=1
[ -z "$FIX_HALO" ]       && FIX_HALO=1
[ -z "$FIX_REFLECTION" ] && FIX_REFLECTION=1

# If you need to force overwrite, add the option here:
[ -z "$LIGHTING_EXTRA" ] && LIGHTING_EXTRA=""

update_ini()
{
	if [ $UPDATE_INI -eq 1 ]; then
		tee -a ../../DX9Settings.ini
	else
		cat > /dev/null
	fi
}

if [ $EXTRACT -eq 1 ]; then
	# Asset bundles are fairly rare, and unlike the .assets files don't
	# appear to have a consistent naming scheme (e.g. LiSBtS had a bunch of
	# *.bytes files under various directories including "DLC", some but not
	# all of which turned out to be these), but this specific file has now
	# been observed in at least two Unity games, including Angry Birds VR
	# (and these games lacked the usual sharedassets files), so adding it
	# on the hunch that it might be some sort of default:
	unity_asset_bundle_extractor.py *_Data/data.unity3d

	unity_asset_extractor.py *_Data/Resources/* *_Data/*.assets
	cd extracted

	extract_unity55_shaders.py */*.shader.raw --type=d3d9
	cd ShaderCRCs
elif [ -d extracted/ShaderCRCs ]; then
	cd extracted/ShaderCRCs
fi

if [ $CLEANUP -eq 1 ]; then
	cleanup_unity_shaders.py ../..
fi

if [ $COPY_TEMPLATE -eq 1 ]; then
	cp -vrT "$DIR/Unity5/DX9-New/ShaderOverride53" ../../ShaderOverride
fi

if [ $FIX_LIGHTING -eq 1 ]; then
	echo
	echo "Applying lighting fix..."
	find . \( -name 05F7E52C.txt \
	       -o -name 5D9CFDD4.txt \
	       -o -name 678DC18B.txt \
	       -o -name 2A3A109D.txt \
	       -o -name BB17C675.txt \
	       \) -a -print0 | xargs -0 dirname -z | sed -z 's/vp$/fp\/????????.txt/' | xargs -0 \
			shadertool.py -I ../.. --fix-unity-lighting-ps-world --only-autofixed $LIGHTING_EXTRA | update_ini
	# TODO: Alternate lighting fix for directional lighting like DX11 template
fi

# TODO: Sun shafts

if [ $FIX_HALO -eq 1 ]; then
	echo
	echo "Applying vertex shader halo & reflection fixes..."
	# TODO: Frustum fix
	shadertool.py -I ../.. --fix-unity-reflection --auto-fix-vertex-halo --add-fog-on-sm3-update --only-autofixed --ignore-register-errors */vp/????????.txt | update_ini
fi

if [ $FIX_REFLECTION -eq 1 ]; then
	echo "Applying pixel shader reflection fix..."
	shadertool.py -I ../.. --fix-unity-reflection --only-autofixed --ignore-register-errors */fp/????????.txt | update_ini
fi
