Texture2D<float4> StereoParams : register(t125);
Texture2D<float4> t100 : register(t100);

void main(float4 pos : SV_Position0, out float4 result : SV_Target0)
{
	float4 stereo = StereoParams.Load(0);

	float width, height;

	t100.GetDimensions(width, height);

	if (stereo.z == -1)
		pos.x += width / 2;

	result = t100.Load(float3(pos.x, pos.y, 0));
}
