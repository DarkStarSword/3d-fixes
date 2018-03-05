Texture2D<float> font : register(t100);

// Edit this line to change the font colour:
static const float3 colour = float3(0.25, 1, 0.25);

struct gs2ps {
	float4 pos : SV_Position0;
	float2 tex : TEXCOORD1;
	uint character : TEXCOORD2;
};

void main(gs2ps input, out float4 o0 : SV_Target0)
{
	float font_width, font_height;
	float2 char_size;
	float2 pos;

	font.GetDimensions(font_width, font_height);
	char_size = float2(font_width, font_height) / float2(16, 6);

	pos.x = (input.character % 16) * char_size.x;
	pos.y = (input.character / 16 - 2) * char_size.y;

	pos.xy += input.tex * char_size;

	o0.xyzw = font.Load(int3(pos, 0)) * float4(colour, 1);

	// Cap alpha to make background dark for contrast:
	o0.w = max(o0.w, 0.75);
}
