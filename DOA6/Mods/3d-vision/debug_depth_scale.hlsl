Texture1D<float4> IniParams : register(t120);
Texture2D<float4> StereoParams : register(t121);

struct vs2ps {
	float4 pos : SV_Position0;
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
	output.uv = output.pos.xy * float2(0.5,-0.5) + 0.5;
}
#endif

#ifdef PIXEL_SHADER
Texture2D<float4> tex : register(t100);

cbuffer slot1 : register(b13)
{
	row_major matrix mW2P;
	row_major matrix mP2W;
}

float z_to_w(float z)
{
	// This is game specific - adjust as needed.
	float4 tmp = mul(float4(0, 0, z, 1), mP2W);
	tmp = tmp / tmp.w;
	tmp = mul(tmp, mW2P);
	return tmp.w;
}

void main(vs2ps input, out float4 result : SV_Target0)
{
	uint width, height;
	tex.GetDimensions(width, height);
	if (!width || !height)
		discard;

	result = tex.Load(int3(input.uv.xy * float2(width, height), 0));
	result = z_to_w(result.x) / StereoParams.Load(0).y;
}
#endif
