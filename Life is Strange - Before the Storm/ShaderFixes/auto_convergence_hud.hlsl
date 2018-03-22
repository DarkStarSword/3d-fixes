// Edit this line to change the font colour:
static const float3 colour = float3(0.25, 1, 0.25);

static const float font_scale = 1.0;
static float2 cur_pos;
static float4 resolution;
static float2 char_size;
static int2 meta_pos_start;

Texture2D<float> font : register(t100);
Texture1D<float4> IniParams : register(t120);
Texture2D<float4> StereoParams : register(t125);

#include "auto_convergence_state.hlsl"
StructuredBuffer<struct auto_convergence_state> state : register(t113);

struct vs2gs {
	uint idx : TEXCOORD0;
};

struct gs2ps {
	float4 pos : SV_Position0;
	float2 tex : TEXCOORD1;
};

#ifdef VERTEX_SHADER
void main(uint id : SV_VertexID, out vs2gs output)
{
	output.idx = id;
}
#endif

#ifdef GEOMETRY_SHADER
void get_meta()
{
	float font_width, font_height;

	resolution = StereoParams.Load(int3(2, 0, 0));

	font.GetDimensions(font_width, font_height);
	char_size = float2(font_width, font_height) / float2(16, 6);

	meta_pos_start = float2(15 * char_size.x, 5 * char_size.y);
}

float2 get_char_dimensions(uint c)
{
	float2 meta_pos;
	float2 dim;

	meta_pos.x = meta_pos_start.x + (c % 16);
	meta_pos.y = meta_pos_start.y + (c / 16 - 2) * 2;

	dim.x = font.Load(int3(meta_pos, 0)) * 255;
	meta_pos.y++;
	dim.y = font.Load(int3(meta_pos, 0)) * 255;

	return dim;
}

void emit_char(uint c, inout TriangleStream<gs2ps> ostream)
{
	float2 cdim = get_char_dimensions(c);
	float2 texcoord;

	if (c >= ' ' && c < 0x7f) {
		gs2ps output;
		float2 dim = float2(cdim.x, char_size.y) / resolution.xy * 2 * font_scale;
		float texture_x_percent = cdim.x / char_size.x;

		texcoord.x = (c % 16) * char_size.x;
		texcoord.y = (c / 16 - 2) * char_size.y;

		output.pos = float4(cur_pos.x        , cur_pos.y - dim.y, 0, 1);
		output.tex = texcoord + float2(0, 1) * char_size;
		ostream.Append(output);
		output.pos = float4(cur_pos.x + dim.x, cur_pos.y - dim.y, 0, 1);
		output.tex = texcoord + float2(texture_x_percent, 1) * char_size;
		ostream.Append(output);
		output.pos = float4(cur_pos.x        , cur_pos.y        , 0, 1);
		output.tex = texcoord + float2(0, 0) * char_size;
		ostream.Append(output);
		output.pos = float4(cur_pos.x + dim.x, cur_pos.y        , 0, 1);
		output.tex = texcoord + float2(texture_x_percent, 0) * char_size;
		ostream.Append(output);

		ostream.RestartStrip();
	}

	// Increment current position taking specific character width into account:
	cur_pos.x += cdim.x / resolution.x * 2 * font_scale;
}

// Using a macro for this because a function requires us to know the size of the buffer
#define EMIT_CHAR_ARRAY(strlen, buf, ostream) \
{ \
	for (uint i = 0; i < strlen; i++) \
		emit_char(buf[i], ostream); \
} \

void print_string_buffer(Buffer<uint> buf, inout TriangleStream<gs2ps> ostream)
{
	uint strlen, i;

	buf.GetDimensions(strlen);

	for (i = 0; i < strlen; i++)
		emit_char(buf[i], ostream);
}

void emit_int(int val, inout TriangleStream<gs2ps> ostream)
{
	int digit;

	if (val < 0.0) {
		emit_char('-', ostream);
		val *= -1;
	}

	int e = 0;
	if (val == 0) {
		emit_char('0', ostream);
		return;
	}
	e = log10(val);
	while (e >= 0) {
		digit = uint(val / pow(10, e)) % 10;
		emit_char(digit + 0x30, ostream);
		e--;
	}
}

// isnan() is optimised out by the compiler, which produces a warning that we
// need the /Gis (IEEE Strictness) option to enable it... but that doesn't work
// either... neither does disabling optimisations... Uhh, good job Microsoft?
// Whatever, just implement it ourselves by testing for an exponent of all 1s
// and a non-zero mantissa:
bool workaround_broken_isnan(float x)
{
	return (((asuint(x) & 0x7f800000) == 0x7f800000) && ((asuint(x) & 0x007fffff) != 0));
}

void emit_float(float val, inout TriangleStream<gs2ps> ostream)
{
	int digit;
	int significant = 0;
	int scientific = 0;

	if (workaround_broken_isnan(val)) {
		emit_char('N', ostream);
		emit_char('a', ostream);
		emit_char('N', ostream);
		return;
	}

	if (val < 0.0) {
		emit_char('-', ostream);
		val *= -1;
	}

	if (isinf(val)) {
		emit_char('i', ostream);
		emit_char('n', ostream);
		emit_char('f', ostream);
		return;
	}

	if (val == 0) {
		emit_char('0', ostream);
		return;
	}

	int e = log10(val);
	if (e < 0) {
		if (e < -4) {
			scientific = --e;
			digit = uint(val / pow(10, e)) % 10;
			emit_char(digit + 0x30, ostream);
			significant++;
			e--;
		} else {
			emit_char('0', ostream);
			e = -1;
		}
	} else {
		if (e > 6)
			scientific = e;
		while (e - scientific >= 0) {
			digit = uint(val / pow(10, e)) % 10;
			emit_char(digit + 0x30, ostream);
			if (digit || significant) // Don't count leading 0 as significant, but do count following 0s
				significant++;
			e--;
		}
	}
	if (!scientific && frac(val / pow(10, e + 1)) == 0)
		return;
	emit_char('.', ostream);
	bool emitted = false;
	while (!emitted || (significant < 3 && frac(val / pow(10, e + 1)))) {
		digit = uint(val / pow(10, e)) % 10;
		emit_char(digit + 0x30, ostream);
		significant++;
		e--;
		emitted = true;
	}

	if (scientific) {
		emit_char('e', ostream);
		emit_int(scientific, ostream);
	}
}

// The max here is dictated by 1024 / sizeof(gs2ps)
[maxvertexcount(168)]
void main(point vs2gs input[1], inout TriangleStream<gs2ps> ostream)
{

	if (!state[0].show_hud || (time - state[0].last_adjust_time > auto_convergence_hud_timeout))
		return;

	get_meta();
	uint idx = input[0].idx;
	float char_height = char_size.y / resolution.y * 2 * font_scale;

	cur_pos = float2(-1, -1 + char_height);

	static const uint AUTO_CONVERGENCE[] =
		{'A', 'u', 't', 'o', '-', 'C', 'o', 'n', 'v', 'e', 'r', 'g', 'e', 'n', 'c', 'e', ' '};
	EMIT_CHAR_ARRAY(17, AUTO_CONVERGENCE, ostream);

	if (auto_convergence_enabled) {
		if (state[0].no_z_buffer) {
			static const uint NO_Z_BUFFER[] =
				{':', ' ', 'N', 'o', ' ', 'Z', ' ', 'B', 'u', 'f', 'f', 'e', 'r'};
			EMIT_CHAR_ARRAY(13, NO_Z_BUFFER, ostream);
		} else {
			static const uint POPOUT[] =
				{'P', 'o', 'p', 'o', 'u', 't', ':', ' '};
			EMIT_CHAR_ARRAY(8, POPOUT, ostream);
			emit_float(ini_popout_bias + state[0].user_popout_bias, ostream);
		}
	} else {
		static const uint DISABLED[] =
			{'D', 'i', 's', 'a', 'b', 'l', 'e', 'd'};
		EMIT_CHAR_ARRAY(8, DISABLED, ostream);
	}
}
#endif

#ifdef PIXEL_SHADER
void main(gs2ps input, out float4 o0 : SV_Target0)
{
	o0.xyzw = font.Load(int3(input.tex, 0)) * float4(colour, 1);

	// Cap alpha to make background dark for contrast:
	o0.w = max(o0.w, 0.75);
}
#endif
