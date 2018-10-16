Texture1D<float4> IniParams : register(t120);

#define amplify (IniParams[7].w ? IniParams[7].w : 1)


struct vs2ps {
	float4 pos : SV_Position0;
	float4 spos : TEXCOORD0;
	float2 uv : TEXCOORD1;
};

#ifdef VERTEX_SHADER
void main(
		out vs2ps output,
		uint vertex : SV_VertexID)
{
	// Not using vertex buffers so manufacture our own coordinates.
	switch(vertex) {
		case 0:
			output.pos.xy = float2(-1, -1);
			break;
		case 1:
			output.pos.xy = float2(-1, 1);
			break;
		case 2:
			output.pos.xy = float2(1, -1);
			break;
		case 3:
			output.pos.xy = float2(1, 1);
			break;
		default:
			output.pos.xy = 0;
			break;
	};
	output.pos.zw = float2(0, 1);
	output.spos = output.pos;
	output.uv = output.pos.xy * float2(0.5,-0.5) + 0.5;
}
#endif

#ifdef PIXEL_SHADER
TextureCube<float4> tex : register(t100);
SamplerState Sampler : register(s0);

void main(vs2ps input, out float4 result : SV_Target0)
{
	uint width, height;
	tex.GetDimensions(width, height);
	if (!width || !height)
		discard;

	result = tex.Sample(Sampler, float3(input.spos.xy * 2, 1)) * amplify;
}
#endif
