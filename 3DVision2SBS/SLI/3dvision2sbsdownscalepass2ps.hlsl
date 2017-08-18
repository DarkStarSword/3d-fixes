Texture2D<float4> StereoParams : register(t125);
Texture1D<float4> IniParams : register(t120);
Texture2D<float4> t100 : register(t100);

void main(float4 pos : SV_Position0, out float4 result : SV_Target0)
{
	float4 stereo = StereoParams.Load(0);
	float mode = IniParams.Load(int2(7, 0)).x;

	float x = pos.x;
	float y = pos.y;
	float width, height;

	t100.GetDimensions(width, height);

	if (mode == 4 || mode == 5) { // Top and bottom
		if (y >= height) {
			y -= height;
			if (mode == 4) {
				x += width / 2;
			}
		} else if (mode == 5) {
			x += width / 2;
		}
	}
	// TODO: Other modes

	result = t100.Load(float3(x, y, 0));
	result.w = 1;
}
