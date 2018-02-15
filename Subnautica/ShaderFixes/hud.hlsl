#define crosshair_visible IniParams[0].x
#define cursor_showing IniParams[7].y
#define texture_filter IniParams[1].y

#define crosshair_texture 2
#define screen_depth_texture 3

#include "crosshair.hlsl"

void handle_hud(inout float4 pos)
{
	float4 s = StereoParams.Load(0);

#ifdef UNITY_PER_DRAW
	if (!all(UNITY_PER_DRAW.unity_ObjectToWorld._m30_m31_m32_m33 == float4(0, 0, 1, 1))) {
		// Tablet or some other in-world HUD
		// Gah, main menu also matches this, so the "Primary" &
		// "Secondary" text in keyboard shortcuts remains adjusted (W
		// ~= 1), while the rest of the menu is at screen depth (W ==
		// 1). The menu actually appears to be positioned in-world then
		// projected back to screen... probably for VR?
		// nvm, it's minor
		return;
	}
#endif

	// Return all HUD items to screen depth:
	if (pos.w != 1)
		pos.x -= s.x * (pos.w - s.y);

	// If the cursor is visible we are in a menu, keep it simple and leave
	// the whole HUD at screen depth so the mouse cursor lines up:
	if (cursor_showing)
		return;

	if (texture_filter == screen_depth_texture)
		return;

	if (texture_filter == crosshair_texture && !crosshair_visible) {
		pos = 0;
		return;
	}

	// Otherwise, adjust to crosshair depth:
	pos.x += adjust_from_depth_buffer(0, 0);
}
