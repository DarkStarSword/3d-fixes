Texture2D<float4> StereoParams : register(t125);
Texture1D<float4> IniParams : register(t120);
Texture2D<float4> t100 : register(t100);

void main(float4 pos : SV_Position0, float4 texcoord: TEXCOORD0, out float4 result : SV_Target0)
{
	float4 stereo = StereoParams.Load(0);
	float4 params = IniParams.Load(0);

	float width, height;

	float x = texcoord.x;
	float y = texcoord.y;

	// Optionally zoom in to somewhat counter VR distortion
	// TODO: Counter it properly
	if (params.x) {
		x = x * 0.65;
		y = y * 0.445;
	}

	// Convert side-by-side to stereo:
	x = x / 2 - 0.5 * stereo.z;

	// Convert to texture coordinates:
	t100.GetDimensions(width, height);
	x = (x / 2 + 0.5) * width;
	y = (y / 2 + 0.5) * height;

	// TODO: Should use interpolation or a sampler here:
	result = t100.Load(float3(x, y, 0));
	result.w = 1;
}
