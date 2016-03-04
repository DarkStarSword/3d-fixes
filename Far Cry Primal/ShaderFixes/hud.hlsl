#include <ShaderFixes/crosshair.hlsl>

bool is_minimap(float4 pos)
{
	return pos.x < -0.4 && pos.y < -0.05;
}

bool is_goals(float4 pos)
{
	return pos.x < 0.15 && pos.y > 0.2;
}

float adjust_hud(float4 pos)
{
	float4 stereo = StereoParams.Load(0);
	float4 params = IniParams.Load(0);
	float width, height;

	ZBuffer.GetDimensions(width, height);
	if (!width)
		return stereo.x * params.x;

	if (is_minimap(pos))
		return stereo.x * params.y;

	if (is_goals(pos))
		return stereo.x * params.z - abs(stereo.x);

	return adjust_from_stereo2mono_depth_buffer(0, 0);
}
