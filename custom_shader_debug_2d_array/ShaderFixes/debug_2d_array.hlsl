Texture2D<float4> StereoParams : register(t125);
Texture1D<float4> IniParams : register(t120);

#define amplify IniParams[0].x
#define scale 1

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
Texture2DArray<float4> tex : register(t100);

void main(vs2ps input, out float4 result : SV_Target0)
{
	uint width, height, len, stack;
	tex.GetDimensions(width, height, len);
	if (!width || !height || !len)
		discard;

	input.pos /= scale;

	float2 resolution = StereoParams.Load(int3(2, 0, 0)).xy;
	stack = resolution.y / height / scale;
	if ((uint)(input.pos.y / height) >= stack)
		discard;

	uint4 p = uint4(input.pos.xy, 0, 0);
	p.z = (uint)input.pos.y / height + (uint)input.pos.x / width * stack;
	if (p.z >= len)
		discard;
	p.x = input.pos.x % width;
	p.y = input.pos.y % height;
	result = tex.Load(p) * amplify;
}
#endif
