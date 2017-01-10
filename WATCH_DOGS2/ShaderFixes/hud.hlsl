#define hud_depth IniParams[0].x
#define hud_depth_mouse_showing IniParams[0].y
#define hud_3d_convergence_override IniParams[0].z
#define hud_3d_convergence_override_mouse_showing IniParams[0].w
#define hud_3d_threshold IniParams[2].z
#define lens_grit_depth IniParams[2].y /* hard coded in asm shaders, do not change */
#define cursor_showing IniParams[1].w
#define scope_convergence_override IniParams[3].x

void to_screen_depth(inout float4 pos)
{
	float4 s = StereoParams.Load(0);

	pos.x -= s.x * (pos.w - s.y);
}

void to_hud_depth(inout float4 pos)
{
	float4 s = StereoParams.Load(0);
	float depth = hud_depth;

	if (cursor_showing)
		depth = hud_depth_mouse_showing;

	pos.x += s.x * depth * pos.w;
}

float2 to_lens_grit_depth(float2 texcoord)
{
	float4 s = StereoParams.Load(0);

	// Adjust depth of dirty lens effect, stretching to avoid the effect clipping
	// at edge of screen:
	float multiplier = s.x * lens_grit_depth;
	if (s.z == 1) /* left eye */
		texcoord.x = (1 + multiplier) * (texcoord.x - 1) + 1;
	else /* right eye */
		texcoord.x *= 1 - multiplier;

	return texcoord;
}

void screen_to_infinity(inout float4 pos)
{
	float4 s = StereoParams.Load(0);

	pos.x += s.x * pos.w;
}

void depth_to_infinity(inout float4 pos)
{
	float4 s = StereoParams.Load(0);

	pos.x += s.x * s.y;
}

void convergence_override(inout float4 pos, float convergence_override)
{
	float4 s = StereoParams.Load(0);

	pos.x += s.x * (s.y - convergence_override);
}

void biased_stereo_correct_with_convergence_override(inout float4 pos, float depth_bias, float convergence_override)
{
	float4 s = StereoParams.Load(0);

	pos.x += s.x * (pos.w + depth_bias - convergence_override) * pos.w / (pos.w + depth_bias);
}

void override_hud_convergence(inout float4 pos)
{
	float4 s = StereoParams.Load(0);
	float world_hud_depth;
	float depth_bias;

	if (cursor_showing) {
		// Mouse cursor showing - override the convergence to a
		// specific value to make the menu easier to use:
		convergence_override(pos, hud_3d_convergence_override_mouse_showing);
		return;
	}

	if (hud_depth == 1) {
		depth_to_infinity(pos);
		return;
	}

	world_hud_depth = -hud_3d_convergence_override / (hud_depth - 1);
	depth_bias = world_hud_depth - hud_3d_convergence_override;

	to_screen_depth(pos);
	biased_stereo_correct_with_convergence_override(pos, depth_bias, hud_3d_convergence_override);
}

void handle_3d_hud(inout float4 pos)
{
	if (pos.w > hud_3d_threshold) // Likely already at correct depth, don't adjust
		return;

	override_hud_convergence(pos);
}

void override_scope_convergence(inout float4 pos)
{
	convergence_override(pos, scope_convergence_override);
}

bool textures_match(Texture2D<float4> tex1, Texture2D<float4> tex2)
{
	uint w1, h1, w2, h2, x, y;

	tex1.GetDimensions(w1, h1);
	tex2.GetDimensions(w2, h2);

	if (w1 != w2 || h1 != h2)
		return false;

	for (y = 0; y < h1; y++) {
		for (x = 0; x < w1; x++) {
			if (any(tex1[uint2(x, y)] != tex2[uint2(x, y)]))
				return false;
		}
	}

	return true;
}
