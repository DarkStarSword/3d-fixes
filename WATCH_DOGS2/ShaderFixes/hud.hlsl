#define hud_depth IniParams[0].x
#define cursor_showing IniParams[1].w

void to_hud_depth(inout float4 pos)
{
	float4 s = StereoParams.Load(0);

	if (cursor_showing)
		return;

	pos.x += s.x * hud_depth * pos.w;
}

void cap_to_hud_depth(inout float4 pos)
{
	// Moves HUD no closer than HUD depth, but could be further
	float4 s = StereoParams.Load(0);
	float world_hud_depth = -s.y / (hud_depth - 1);

	if (s.y && pos.w > 0 && (pos.w < world_hud_depth || isinf(world_hud_depth))) {
		pos.x -= s.x * (pos.w - s.y);
		to_hud_depth(pos);
	}
}

void to_screen_depth(inout float4 pos)
{
	float4 s = StereoParams.Load(0);

	pos.x -= s.x * (pos.w - s.y);
}
