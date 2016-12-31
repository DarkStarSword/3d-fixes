Texture2D<float4> before : register(t100);
Texture2D<float4> after : register(t101);
Texture1D<float4> IniParams : register(t120);

void main(float4 pos : SV_Position0, float4 spos: TEXCOORD0, float2 tpos: TEXCOORD1, out float4 result : SV_Target0)
{
	uint width, height;
	before.GetDimensions(width, height);

	result = after.Load(int3(tpos.xy * float2(width, height), 0))
	      - before.Load(int3(tpos.xy * float2(width, height), 0));
}
