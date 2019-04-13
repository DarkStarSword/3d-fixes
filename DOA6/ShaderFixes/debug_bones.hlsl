#define colour IniParams[0]
#define first IniParams[1].x
static const float size = 0.004;

Texture1D<float4> IniParams : register(t120);
Texture2D<float4> StereoParams : register(t121);

struct vs2gs {
	float4 pos : SV_Position;
	float node_idx_percent : TEXCOORD;
};

struct gs2ps {
	float4 pos : SV_Position0;
	float node_idx_percent : TEXCOORD;
};

#ifdef VERTEX_SHADER
cbuffer Globals : register(b0)
{
  row_major float4x4 mW2P;           // Index:    0 1 2 3          Components:    16
  float4x3 mL2W[128];                  // Index:    4-387            Components:  1536
  bool bSkin[3];                     // Index:  388-390.x          Components:     9
  row_major float4x4 mW2Pt;          // Index:  391 392 393 394    Components:    16
  row_major float4x4 mW2S[4];        // Index:  395-410            Components:    64
}

void main(uint id : SV_VertexID, out vs2gs output)
{
	float4 pos = float4(0,0,0,1);

	output.node_idx_percent = (float)id / 128;
	output.pos = mul(float4(mul(pos, mL2W[first + id]), 1), mW2P);
	// Running with no depth buffer assigned so driver won't have stereo corrected:
	//float4 stereo = StereoParams.Load(0);
	//output.pos.x += stereo.x * (output.pos.w - stereo.y);
}
#endif

#ifdef GEOMETRY_SHADER
[maxvertexcount(6)]
void main(point vs2gs input[1], inout TriangleStream<gs2ps> ostream)
{
	gs2ps output;

	output.node_idx_percent = input[0].node_idx_percent;
	if (input[0].pos.w) {
		output.pos = float4(input[0].pos) + float4(-size, -size, 0, 0) * input[0].pos.w;
		ostream.Append(output);
		output.pos = float4(input[0].pos) + float4(+size, -size, 0, 0) * input[0].pos.w;
		ostream.Append(output);
		output.pos = float4(input[0].pos) + float4(-size, +size, 0, 0) * input[0].pos.w;
		ostream.Append(output);
		output.pos = float4(input[0].pos) + float4(+size, +size, 0, 0) * input[0].pos.w;
		ostream.Append(output);
	}
}
#endif

#ifdef PIXEL_SHADER
void main(gs2ps input, out float4 o0 : SV_Target0, out float depth : SV_Depth)
{
	o0 = colour; // * (0.05 + input.node_idx_percent * 0.95);
	// Set output depth to 1 so nothing else will clobber this on the render target
	depth = 1;
}
#endif
