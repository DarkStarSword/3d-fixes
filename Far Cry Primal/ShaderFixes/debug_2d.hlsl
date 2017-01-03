Texture2D<float4> tex : register(t100);
Texture1D<float4> IniParams : register(t120);

void main(float4 pos : SV_Position0, float4 spos: TEXCOORD0, float2 tpos: TEXCOORD1, out float4 result : SV_Target0)
{
	uint width, height;
	tex.GetDimensions(width, height);
	if (!width || !height)
		discard;

	result = tex.Load(int3(tpos.xy * float2(width, height), 0));
	// Debugging some of the specular shaders like 89d9cb3e7678ac50:
	// result = abs(result) / 10000;
}
