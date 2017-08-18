Texture2D<float4> t100 : register(t100);

void main(float4 pos : SV_Position0, out float4 result : SV_Target0)
{
	float x = pos.x;
	float y = pos.y;
	y *= 2;
	result = (t100.Load(float3(x, y    , 0)) +
		  t100.Load(float3(x, y + 1, 0))) / 2;
	result.w = 1;
}
