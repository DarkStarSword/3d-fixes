#!/bin/sh -e

DIR="$(readlink -f "$(dirname $0)/../..")"
. "$DIR/Unity5/DX11/checkenv.sh"

# You can now pass these options in via environment variables, like:
# EXTRACT=0 ~/3d-fixes/Unity5/DX11/autofix55.sh
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
		tee -a ../../ShaderFixes/unity_generated.ini
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

	unity_asset_extractor.py *_Data/Resources/unity* *_Data/*.assets
	cd extracted

	extract_unity55_shaders.py */*.shader.raw --type=d3d11
	cd ShaderFNVs
elif [ -d extracted/ShaderFNVs ]; then
	cd extracted/ShaderFNVs
fi

if [ $CLEANUP -eq 1 ]; then
	cleanup_unity_shaders.py ../..
fi

if [ $COPY_TEMPLATE -eq 1 ]; then
	cp -vr "$DIR/Unity5/DX11/ShaderFixes" ../..
fi

if [ $FIX_LIGHTING -eq 1 ]; then
	# Lighting fix - match any shaders that use known lighting vertex shaders:
	echo
	echo "Applying point/spot/physical lighting fix..."
	find . \( -name 'b78925705424e647-vs*' \
	       -o -name 'ca5cfc8e4d8b1ce5-vs*' \
	       -o -name '69294277cca1bade-vs*' \
	       -o -name '99341a34a001a3d1-vs*' \
	       -o -name '94a6d6474c5424ae-vs*' \
	       -o -name '4a87a6742ed6d7a9-vs*' \
	       -o -name '4c9936f7f1d28f6e-vs*' \
	       -o -name '65640cd671a89091-vs*' \
	       \) -a -print0 | xargs -0 dirname -z | sort -uz | sed -z 's/$/\/*-ps.txt/' | xargs -0 \
			asmtool.py -I ../.. --fix-unity-lighting-ps --only-autofixed $LIGHTING_EXTRA | update_ini
	echo
	echo "Applying directional lighting fix..."
	find . \( -name 'bfae1ae6908d87a2-vs*' \
	       -o -name 'f51c2a7085326040-vs*' \
	       -o -name 'f1dfaa0a76663bf9-vs*' \
	       -o -name 'bc1b4298b3713fce-vs*' \
	       -o -name '28a7271021d7155a-vs*' \
	       -o -name '2917d6a2498642c6-vs*' \
	       \) -a -print0 | xargs -0 dirname -z | sort -uz | sed -z 's/$/\/*-ps.txt/' | xargs -0 \
			asmtool.py -I ../.. --fix-unity-lighting-ps=TEXCOORD4 --only-autofixed $LIGHTING_EXTRA | update_ini
fi

if [ $FIX_SUN_SHAFTS -eq 1 ]; then
	echo
	echo "Applying sun shaft fix..."
	hlsltool.py -I ../.. --fix-unity-sun-shafts --only-autofixed --fxc "$FXC" Hidden_SunShaftsComposite/*_replace.txt | update_ini
fi

if [ $FIX_HALO -eq 1 ]; then
	echo
	echo "Applying vertex shader halo, reflection & frustum fixes..."
	asmtool.py -I ../.. --auto-fix-vertex-halo --fix-unusual-halo-with-inconsistent-w-optimisation --fix-unity-reflection --fix-unity-frustum-world --only-autofixed */*vs.txt | update_ini
fi

if [ $FIX_REFLECTION -eq 1 ]; then
	echo "Applying pixel shader reflection fix..."
	asmtool.py -I ../.. --fix-unity-reflection --only-autofixed */*ps.txt | update_ini
fi
