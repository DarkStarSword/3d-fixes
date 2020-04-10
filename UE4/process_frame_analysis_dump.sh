#!/bin/sh -e

DIR=~/3d-fixes
PATH="$DIR:$PATH"

analyse_dir="$1"
sha_match="$2" # FIXME: Better way to specify this
driver_stereo_cb=12

if [ ! -d "$analyse_dir" -o -z "$sha_match" ]; then
	echo "usage: $0 FrameAnalysis sha1_of_FViewUniformShaderParameters_in_frame"
	exit 1
fi

SHA1_LIST_FILE=$(mktemp)
cleanup()
{
	if [ -f "$SHA1_LIST_FILE" ]; then
		rm "$SHA1_LIST_FILE"
	fi
}
trap cleanup EXIT

update_ini()
{
	dos2unix | tee -a ../d3dx.ini
}

cd "$analyse_dir"
sha1sum *.buf > "$SHA1_LIST_FILE"

for shader_type in vs hs ds gs ps cs; do
	echo "Searching for $shader_type using matching cbuffer..." >&2
	match=$(grep "$sha_match .*-$shader_type-cb.*\.buf" "$SHA1_LIST_FILE") || continue
	match=$(echo "$match" | sed -E "s/^.*-$shader_type=([0-9a-fA-F]{16}).*$/\1/" | sort -u)
	for shader_hash in $match; do
		shader_filename="../ShaderCache/$shader_hash-$shader_type.txt"
		remap_cmds=
		cbuffers=$(grep "$sha_match .*-$shader_type-cb.*-$shader_type=$shader_hash" "$SHA1_LIST_FILE" | sed -E 's/^.*-cb([0-9]+)-.*$/\1/' | sort -u)
		used_cbuffers=
		for cbuffer in $cbuffers; do
			# Make sure that the shader uses it:
			grep "dcl_constantbuffer cb$cbuffer\[" "$shader_filename" || continue
			used_cbuffers="$used_cbuffers $cbuffer"
			remap_cmds=$(printf "%s --remap-cb %d 1%02d" "$remap_cmds" "$cbuffer" "$cbuffer")
		done
		if [ -z "$used_cbuffers" ]; then
			continue
		fi

		asmtool.py $remap_cmds -i --only-autofixed --disable-driver-stereo-cb $driver_stereo_cb "$shader_filename" || continue

		printf "\n" | update_ini
		printf "[ShaderOverride_UE4_FViewUniformShaderParameters-%s=%s]\n" "$shader_type" "$shader_hash" | update_ini
		printf "allow_duplicate_hash = true\n" | update_ini
		printf "hash = %s\n" "$shader_hash" | update_ini
		# Prevent future frame analysis dumps from including this one:
		# printf "analyse_options = log\n" | update_ini
		for cbuffer in $used_cbuffers; do
			# These first two lines are only necessary for the first matching cbuffer
			printf "ResourceFViewUniformShaderParameters_Mono_CB = ref %s-cb%d\n" "$shader_type" "$cbuffer" | update_ini
			printf "run = CustomShader_Stereoise_FViewUniformShaderParameters\n" | update_ini
			printf "%s-t1%02d = ResourceFViewUniformShaderParameters_Stereo_SRV_UAV\n" "$shader_type" "$cbuffer" | update_ini
			printf "post %s-t1%02d = null\n" "$shader_type" "$cbuffer" | update_ini
		done
		echo
	done
done
