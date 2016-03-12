#include <crosshair.hlsl>

float hud_adjustment_from_depth_buffer(int samples_x, int samples_y, float min_allowed)
{
#define FLT_MAX 0x7f7fffff
	float4 stereo = StereoParams.Load(0);
	float separation = stereo.x; float convergence = stereo.y;
	float w, w_sum = 0, w_min = FLT_MAX, w_max = 0;
	int x, y;

	for (y = 0; y < samples_y; y++) {
		for (x = 0; x < samples_x; x++) {
			w = world_z_from_depth_buffer(
				((float)x / (samples_x-1) * 2 - 1) * 0.75,
				((float)y / (samples_y-1) * 2 - 1) * 0.5);
			w_sum += w;
			w_min = min(w_min, w);
			w_max = max(w_max, w);
		}
	}

	// Average:
	// w = w_sum / (samples_x * samples_y);
	w = max(w_min, min_allowed);

	return separation * (w - convergence) / w;
}

bool is_minimap(float4 pos, float4 params1)
{
	return !params1.x && pos.x < -0.4 && pos.y < -0.05;
}

bool is_subtitle(float4 pos)
{
	return pos.y < -0.7;
}

bool is_goals(float4 pos, float4 params1)
{
	return params1.y == 3 && pos.x < 0.15 && pos.y > 0.2;
}

bool is_crosshair(float4 pos, float4 params1)
{
	return (all(abs(pos.xy) < 0.10 * pos.w));

	// Let's wait until I've reworked the texture hashes for a faster
	// track_resource_updates before we use texture filtering:
	// return (params1.y == 2);
}

float adjust_hud(float4 pos, bool crosshair_shader)
{
	float4 stereo = StereoParams.Load(0);
	float4 params0 = IniParams.Load(0);
	float4 params1 = IniParams.Load(int2(1, 0));
	float4 params2 = IniParams.Load(int2(2, 0));
	float width, height;
	float adj = 0;

	if (params1.z == 2) // Video playing
		return 0;

	if (params1.z == 1) // Menu background
		return stereo.x * params0.x;

	ZBuffer.GetDimensions(width, height);
	if (!width)
		return stereo.x * params0.x;

	switch (params2.x) {
	case 0:
		return stereo.x * params0.x;
	case 1:
		adj = adjust_from_stereo2mono_depth_buffer(0, 0);
		break;
	case 2:
		adj = hud_adjustment_from_depth_buffer(12, 3, params2.y);
		break;
	}

	if (is_goals(pos, params1)) {
		// return stereo.x * params0.z - abs(stereo.x);
		return adj - abs(stereo.x);
	}

	return adj;

// Hunting tutorial is messed up - will really need texture
// filtering to whitelist elements.
#if 0
	if (is_minimap(pos, params1))
		return stereo.x * params0.y;

	if (is_subtitle(pos))
		return stereo.x * params0.w;

	if (crosshair_shader && is_crosshair(pos, params1))
		return adjust_from_stereo2mono_depth_buffer(0, 0);

	return stereo.x * params0.x;
#endif
}
