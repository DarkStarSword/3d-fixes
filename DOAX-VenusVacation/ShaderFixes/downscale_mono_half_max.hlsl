Texture2D<float> t110 : register(t110);

void main(float4 pos : SV_Position0, out float result : SV_Target0)
{
	float x = floor(pos.x) * 2;
	float y = floor(pos.y) * 2;

	result =     t110.Load(float3(x + 0, y + 0, 0));
	result = max(t110.Load(float3(x + 1, y + 0, 0)), result);
	result = max(t110.Load(float3(x + 0, y + 1, 0)), result);
	result = max(t110.Load(float3(x + 1, y + 1, 0)), result);
}
