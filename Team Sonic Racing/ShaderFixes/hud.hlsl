// We want to adjust the HUD so that nameplates, warning icons, etc line up
// with the player / item they correspond with, but there are a few problems:
//
// 1. Split screen. The game draws the four worlds first (top left, top right,
// bottom left, bottom right), then blits them to their final locations on the
// screen and draws the HUD over the top. This means that the most recent depth
// buffer, etc. won't correspond to the HUD being drawn, and we would have to
// reliably track up to four depth buffers to consider using a crosshair.hlsl
// style fix.
//
// 2. Mirror mode. If we use the depth buffer and mirror mode is enabled we
// would need to mirror the X sample locations.
//
// For now we will do something simpler, that will hopefully work out
// acceptably.

#define hud_active IniParams[0].x
#define min_hud IniParams[0].y
#define max_hud IniParams[0].z
#define hud_amount IniParams[0].w

void adjust_hud(inout float4 pos)
{
	float4 s = StereoParams.Load(0);

	// Avoid adjusting full screen shaders blitting the world to the screen,
	// particularly problematic in the character select trying to zoom in:
	if (any(pos.xy >= pos.w * 0.99))
		return;

	if (pos.w == 1.0 && hud_active) {
		float y = pos.y / 2 + 0.5;
		float depth = lerp(min_hud, max_hud, y);
		pos.x += s.x * (depth - s.y) / depth * hud_amount;
	}
}
