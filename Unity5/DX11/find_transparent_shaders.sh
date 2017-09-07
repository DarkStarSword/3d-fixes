#!/bin/sh

# Subshader tag reference:
# https://docs.unity3d.com/462/Documentation/Manual/SL-SubshaderTags.html

# Pass tag reference:
# https://docs.unity3d.com/462/Documentation/Manual/SL-PassTags.html

include_transparent_tags()
{
	# Include only shaders that use *both* QUEUE=Transparent and RenderType=Transparent
	xargs -0 grep -Zl 'Tags {.*"QUEUE"="Transparent".*"RenderType"="Transparent"'
}

exclude_any_non_transparent_render_type()
{
	# Excludes any shader that has *any* Tags missing RenderType=Transparent
	xargs -0 grep -PLZ 'Tags { ((?!"RenderType"="Transparent").)*$'
}

exclude_any_non_transparent_queues()
{
	# Excludes any shader that has *any* Tags missing QUEUE=Transparent
	xargs -0 grep -PLZ 'Tags { ((?!"QUEUE"="Transparent").)*$'
}

exclude_deferred_lighting()
{
	# Filter out shaders based on their lighting mode, for now I'm thinking:
	# Allow:
	#   Always: Always rendered; no lighting is applied.
	#   ForwardBase: Used in Forward rendering, ambient, main directional light and vertex/SH lights are applied.
	#   ForwardAdd: Used in Forward rendering; additive per-pixel lights are applied, one pass per light.
	#   Vertex: Used in Vertex Lit rendering when object is not lightmapped; all vertex lights are applied.
	#   VertexLMRGBM: Used in Vertex Lit rendering when object is lightmapped; on platforms where lightmap is RGBM encoded.
	#   VertexLM: Used in Vertex Lit rendering when object is lightmapped; on platforms where lightmap is double-LDR encoded (generally mobile platforms and old dekstop GPUs).
	# Exclude:
	#   PrepassBase: Used in Deferred Lighting, renders normals and specular exponent.
	#   PrepassFinal: Used in Deferred Lighting, renders final color by combining textures, lighting and emission.
	#   ShadowCaster: Renders object as shadow caster.
	#   ShadowCollector: Gathers object’s shadows into screen-space buffer for Forward rendering path.
	#   Deferred - NOT DOCUMENTED?

	xargs -0 grep -ZL 'Tags {.*"LIGHTMODE"="PrePass' | \
	xargs -0 grep -ZL 'Tags {.*"LIGHTMODE"="Shadow' | \
	xargs -0 grep -ZL 'Tags {.*"LIGHTMODE"="Deferred'
}

include_zwrite_off_only()
{
	# Will not include any shaders with a mix of on and off - only includes
	# shaders that are always ZWrite Off
	xargs -0 grep -Zl '\/\/\s*ZWrite Off'
}

strip_comments()
{
	sed 's/\/\/\s*//'
}

find_vertex_shaders()
{
	find . -name '*-vs.txt' -print0
}

find_pixel_shaders()
{
	find . -name '*-ps.txt' -print0
}

strip_cwd()
{
	sed -z 's/^\.\///'
}

nul_to_newlines()
{
	xargs -0 -n 1 echo
}

get_hash_from_filename()
{
	echo "$@" | sed 's/^.*\///; s/-.s\.txt$//'
}

format_shader_override()
{
	while read filename; do
		hash=$(get_hash_from_filename "$filename")
		cat << EOF
[ShaderOverride_Transparent_Depth_Buffer: $filename]
allow_duplicate_hash = true
hash = $hash
run = CustomShader_Render_Transparent_Depth_Buffer
EOF
	done
}

remove_duplicate_hashes()
{
	# -z flag for zero terminated makes this fail, so do this after nul_to_newlines
	sort -t \/ -k 2 -u
}

if [ $(basename "$PWD") != ShaderFNVs ]; then
	echo Must run this from ShaderFNVs
	exit 1
fi

find_pixel_shaders \
	| include_zwrite_off_only \
	| include_transparent_tags \
	| exclude_any_non_transparent_queues \
	| exclude_any_non_transparent_render_type \
	| exclude_deferred_lighting \
	| strip_cwd \
	| nul_to_newlines \
	| remove_duplicate_hashes \
	| sort \
	| format_shader_override
