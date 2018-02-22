Texture2D<float> font : register(t100);
Texture1D<float4> IniParams : register(t120);
Texture2D<float4> StereoParams : register(t125);

static const float font_scale = 1.0;
static float2 cur_pos;
static float4 resolution;
static float2 char_size;
static int2 meta_pos_start;

static const uint STRUCT[] = {'S', 't', 'r', 'u', 'c', 't', ' '};
static const uint BUFFER[] = {'B', 'u', 'f', 'f', 'e', 'r', ' '};
static const uint PS[] = {'P', 'S', ' '};
static const uint CS[] = {'C', 'S', ' '};
static const uint RTV[] = {'R', 'T', 'V'};
static const uint SRV[] = {'S', 'R', 'V'};
static const uint UAV[] = {'U', 'A', 'V'};
static const uint ARROW[] = {' ', '-', '>', ' '};
static const uint LEFT[] = {'L', 'E', 'F', 'T'};
static const uint RIGHT[] = {'R', 'I', 'G', 'H', 'T'};
static const uint INVALID[] = {'I', 'N', 'V', 'A', 'L', 'I', 'D'};

Buffer<uint> title : register(t105);

Buffer<float> t50 : register(t50);
Buffer<float> t51 : register(t51);
Buffer<float> t52 : register(t52);
Buffer<float> t53 : register(t53);
Buffer<float> t54 : register(t54);
Buffer<float> t55 : register(t55);
Buffer<float> t56 : register(t56);
Buffer<float> t57 : register(t57);
Buffer<float> t58 : register(t58);

StructuredBuffer<float> t59 : register(t59);
StructuredBuffer<float> t60 : register(t60);
StructuredBuffer<float> t61 : register(t61);
StructuredBuffer<float> t62 : register(t62);

struct vs2gs {
	uint idx : TEXCOORD0;
};

struct gs2ps {
	float4 pos : SV_Position0;
	float2 tex : TEXCOORD1;
	uint character : TEXCOORD2;
};

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

	// This does not emit space characters, but if you want to shade the
	// background of the text you will need to change the > to a >= here
	if (c > ' ' && c < 0x7f) {
		gs2ps output;
		float2 dim = float2(cdim.x, char_size.y) / resolution.xy * 2 * font_scale;
		float texture_x_percent = cdim.x / char_size.x;

		output.character = c;

		output.pos = float4(cur_pos.x        , cur_pos.y - dim.y, 0, 1);
		output.tex = float2(0, 1);
		ostream.Append(output);
		output.pos = float4(cur_pos.x + dim.x, cur_pos.y - dim.y, 0, 1);
		output.tex = float2(texture_x_percent, 1);
		ostream.Append(output);
		output.pos = float4(cur_pos.x        , cur_pos.y        , 0, 1);
		output.tex = float2(0, 0);
		ostream.Append(output);
		output.pos = float4(cur_pos.x + dim.x, cur_pos.y        , 0, 1);
		output.tex = float2(texture_x_percent, 0);
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
	while (!emitted || (significant < 6 && frac(val / pow(10, e + 1)))) {
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
[maxvertexcount(144)]
void main(point vs2gs input[1], inout TriangleStream<gs2ps> ostream)
{
	get_meta();
	uint idx = input[0].idx;
	uint i = 0;
	uint start_pos = idx + IniParams[7].w;
	float cval = 1.#INF;
	float char_height = char_size.y / resolution.y * 2 * font_scale;
	int max_y = resolution.y / char_size.y * font_scale;

	cur_pos = float2(-1 + (start_pos / max_y * 0.32), 1 - (start_pos % max_y) * char_height);
	if (cur_pos.x >= 1)
		return;

	if (idx == i++) {
		print_string_buffer(title, ostream);
		return;
	} else if (idx == i++) {
		cval = t50[0];
		EMIT_CHAR_ARRAY(7, BUFFER, ostream);
		EMIT_CHAR_ARRAY(3, PS, ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, SRV, ostream);
	} else if (idx == i++) {
		cval = t51[0];
		EMIT_CHAR_ARRAY(7, BUFFER, ostream);
		EMIT_CHAR_ARRAY(3, PS, ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		EMIT_CHAR_ARRAY(4, ARROW, ostream);
		EMIT_CHAR_ARRAY(3, SRV, ostream);
	} else if (idx == i++) {
		cval = t52[0];
		EMIT_CHAR_ARRAY(7, BUFFER, ostream);
		EMIT_CHAR_ARRAY(3, PS, ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		EMIT_CHAR_ARRAY(4, ARROW, ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, SRV, ostream);
	} else if (idx == i++) {
		cval = t53[0];
		EMIT_CHAR_ARRAY(7, BUFFER, ostream);
		EMIT_CHAR_ARRAY(3, PS, ostream);
		emit_char('(', ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		emit_char(')', ostream);
		emit_char(' ', ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, SRV, ostream);
	} else if (idx == i++) {
		cval = t54[0];
		EMIT_CHAR_ARRAY(7, BUFFER, ostream);
		EMIT_CHAR_ARRAY(3, PS, ostream);
		emit_char('(', ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		emit_char(')', ostream);
		emit_char(' ', ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, SRV, ostream);
	} else if (idx == i++) {
		cval = t55[0];
		EMIT_CHAR_ARRAY(7, BUFFER, ostream);
		EMIT_CHAR_ARRAY(3, CS, ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, SRV, ostream);
	} else if (idx == i++) {
		cval = t56[0];
		EMIT_CHAR_ARRAY(7, BUFFER, ostream);
		EMIT_CHAR_ARRAY(3, CS, ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, SRV, ostream);
	} else if (idx == i++) {
		cval = t57[0];
		EMIT_CHAR_ARRAY(7, BUFFER, ostream);
		EMIT_CHAR_ARRAY(3, CS, ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		EMIT_CHAR_ARRAY(4, ARROW, ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, SRV, ostream);
	} else if (idx == i++) {
		cval = t58[0];
		EMIT_CHAR_ARRAY(7, BUFFER, ostream);
		EMIT_CHAR_ARRAY(3, CS, ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		EMIT_CHAR_ARRAY(4, ARROW, ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, SRV, ostream);
	} else if (idx == i++) {
		cval = t59[0];
		EMIT_CHAR_ARRAY(7, STRUCT, ostream);
		EMIT_CHAR_ARRAY(3, CS, ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		EMIT_CHAR_ARRAY(4, ARROW, ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, SRV, ostream);
	} else if (idx == i++) {
		cval = t60[0];
		EMIT_CHAR_ARRAY(7, STRUCT, ostream);
		EMIT_CHAR_ARRAY(3, CS, ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		EMIT_CHAR_ARRAY(4, ARROW, ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, SRV, ostream);
	} else if (idx == i++) {
		cval = t61[0];
		EMIT_CHAR_ARRAY(7, STRUCT, ostream);
		EMIT_CHAR_ARRAY(3, CS, ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, SRV, ostream);
		EMIT_CHAR_ARRAY(4, ARROW, ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, SRV, ostream);
	} else if (idx == i++) {
		cval = t62[0];
		EMIT_CHAR_ARRAY(7, STRUCT, ostream);
		EMIT_CHAR_ARRAY(3, CS, ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, SRV, ostream);
		EMIT_CHAR_ARRAY(4, ARROW, ostream);
		EMIT_CHAR_ARRAY(3, UAV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, RTV, ostream);
		emit_char('+', ostream);
		EMIT_CHAR_ARRAY(3, SRV, ostream);
	} else {
		return;
	};

	emit_char(':', ostream);
	emit_char(' ', ostream);

	if (cval == 1.0) {
		EMIT_CHAR_ARRAY(4, LEFT, ostream);
	} else if (cval == -1.0) {
		EMIT_CHAR_ARRAY(5, RIGHT, ostream);
	} else if (cval == 0.0) {
		EMIT_CHAR_ARRAY(7, INVALID, ostream);
	} else {
		emit_float(cval, ostream);
	}
}
