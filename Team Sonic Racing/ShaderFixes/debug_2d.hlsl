Texture1D<float4> IniParams : register(t120);

#define amplify IniParams[0].x
#define flip IniParams[0].y
#define channel IniParams[0].z
#define power IniParams[0].w

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

void main(vs2ps input, out float4 result : SV_Target0)
{
	uint width, height;
	tex.GetDimensions(width, height);
	if (!width || !height)
		discard;

	if (flip)
		input.uv.y = 1 - input.uv.y;

	result = tex.Load(int3(input.uv.xy * float2(width, height), 0)) * amplify;
	if (channel == 1)
		result = result.x;
	else if (channel == 2)
		result = result.y;
	else if (channel == 3)
		result = result.z;
	else if (channel == 4)
		result = result.w;

	result = pow(abs(result), power);
}
#endif
