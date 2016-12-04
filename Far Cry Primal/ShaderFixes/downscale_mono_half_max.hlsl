Texture2D<float> t100 : register(t100);

void main(float4 pos : SV_Position0, out float result : SV_Target0)
{
	float x = pos.x * 2;
	float y = pos.y * 2;

	result =     t100.Load(float3(x + 0, y + 0, 0));
	result = max(t100.Load(float3(x + 1, y + 0, 0)), result);
	result = max(t100.Load(float3(x + 0, y + 1, 0)), result);
	result = max(t100.Load(float3(x + 1, y + 1, 0)), result);
}
