Texture2D<float> font : register(t100);
Texture2D<float4> StereoParams : register(t125);
Texture2D<float4> tex1 : register(t101);
Texture2D<float4> tex2 : register(t102);

static const float font_scale = 1.0;
static float2 cur_pos;
static float4 resolution;
static float2 char_size;
static int2 meta_pos_start;

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
	if (c > ' ' && c < 0x7f) {
		gs2ps output;
		// Not taking specific character width into account for simplicity.
		// Could save some pixels by doing so, but who cares?
		float2 dim = char_size / resolution.xy * 2 * font_scale;

		output.character = c;

		output.pos = float4(cur_pos.x        , cur_pos.y - dim.y, 0, 1);
		output.tex = float2(0, 1);
		ostream.Append(output);
		output.pos = float4(cur_pos.x + dim.x, cur_pos.y - dim.y, 0, 1);
		output.tex = float2(1, 1);
		ostream.Append(output);
		output.pos = float4(cur_pos.x        , cur_pos.y        , 0, 1);
		output.tex = float2(0, 0);
		ostream.Append(output);
		output.pos = float4(cur_pos.x + dim.x, cur_pos.y        , 0, 1);
		output.tex = float2(1, 0);
		ostream.Append(output);

		ostream.RestartStrip();
	}

	// Increment current position taking specific character width into account:
	float2 cdim = get_char_dimensions(c);
	cur_pos.x += cdim.x / resolution.x * 2 * font_scale;
}

void emit_hex(uint val, inout TriangleStream<gs2ps> ostream)
{
	uint char, i;

	for (i = 0; i < 8; i++) {
		char = (val >> i*4) & 0xf;
		if (char < 10)
			emit_char('0' + char, ostream);
		else
			emit_char('a' + char - 10, ostream);
	}
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
		digit = int(val / pow(10, e)) % 10;
		emit_char(digit + 0x30, ostream);
		e--;
	}
}

void emit_float(float val, inout TriangleStream<gs2ps> ostream)
{
	int digit;
	int significant = 0;
	int scientific = 0;

	if (isnan(val)) {
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
		emit_char('0', ostream);
	} else {
		if (e > 6)
			scientific = e;
		while (e - scientific >= 0) {
			digit = int(val / pow(10, e)) % 10;
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
		digit = int(val / pow(10, e)) % 10;
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
	float char_height = char_size.y / resolution.y * 2 * font_scale;
	int max_y = resolution.y / char_size.y * font_scale;

	uint w, h, x, y;
	tex1.GetDimensions(w, h);
	x = idx % w;
	y = idx / w;
	float4 tval = tex1[int2(x, y)] - tex2[int2(x, y)];

	cur_pos = float2(-1 + (idx / max_y * 0.32), 1 - (idx % max_y) * char_height);
	if (cur_pos.x >= 1)
		return;

	emit_int(idx, ostream);
	emit_char(':', ostream);
	emit_char(' ', ostream);
	emit_float(tval.x, ostream);
	emit_char(' ', ostream);
	emit_float(tval.y, ostream);
	emit_char(' ', ostream);
	emit_float(tval.z, ostream);
	emit_char(' ', ostream);
	emit_float(tval.w, ostream);
}
