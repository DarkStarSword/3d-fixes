Texture2D<float4> StereoParams : register(t121);
Texture1D<float4> IniParams : register(t120);

#define amplify IniParams[0].x
#define scale IniParams[0].y

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
Texture3D<float> volume : register(t100);

void main(vs2ps input, out float4 result : SV_Target0)
{
	uint width, height, depth, stack;
	volume.GetDimensions(width, height, depth);

	input.pos /= scale;
	stack = 1080 / height / scale;
	if ((uint)input.pos.y / height > stack)
		discard;

	uint4 p = uint4(input.pos.xy, 0, 0);
	p.z = (uint)input.pos.y / height + (uint)input.pos.x / width * stack;
	p.x = input.pos.x % width;
	p.y = input.pos.y % height;
	result = volume.Load(p) * amplify;
	//result.w = (p.z < depth) * (input.pos.x < width * 5) * 0.75;
	result.w = (p.z < depth) * 0.75;
}
#endif
