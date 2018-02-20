#define crosshair_visible IniParams[0].x
#define hud_w1_tolerance IniParams[0].y
#define hud_x_cutoff IniParams[0].z
#define hud_y_cutoff IniParams[0].w
#define cursor_showing IniParams[7].y
#define texture_filter IniParams[1].y
#define pda_preset IniParams[1].z
#define loading_screen_preset IniParams[1].w

#define crosshair_texture 2
#define screen_depth_texture 3

#include "crosshair.hlsl"

void handle_in_world_hud(inout float4 pos)
{
	float4 s = StereoParams.Load(0);

	// Tablet, in-world WARNING display or some other in-world HUD
	// Stupidly (and probably because of VR), this game projects a lot of
	// HUD in world, then projects them back to screen space, so this
	// matches more than you would expect. This affects the main menu and
	// the popup box that appears when mousing over the icons at the bottom
	// of the screen in the PDA, and the icons in the fabricator.

	// Because of this double-projection the W==1 driver heuristic doesn't
	// work due to floating point error, so we increase the tolerance
	// ourselves to return things to screen depth.
	if (pos.w != 1 && distance(pos.w, 1) < hud_w1_tolerance)
		pos.x -= s.x * (pos.w - s.y);
}

bool is_fullscreen(float4 pos)
{
	return all(abs(pos.xy) > 0.99);
}

#ifdef UNITY_PER_DRAW
bool is_in_world_hud()
{
	return !all(UNITY_PER_DRAW.unity_ObjectToWorld._m30_m31_m32_m33 == float4(0, 0, 1, 1));
}
#else
bool is_in_world_hud()
{
	return false;
}
#endif

bool is_hud_depth_pass()
{
	uint width, height;

	InWorldHUDZBuffer.GetDimensions(width, height);

	return (width == 0);
}

void handle_hud_depth_pass(inout float4 pos, float4 color)
{
	if (!is_in_world_hud()) {
		pos = 0;
		return;
	}

	if (color.w == 0) {
		// Prevent considering the warning display in middle of the the
		// Cyclops cockpit when it is invisible
		pos = 0;
		return;
	}
}

void handle_hud(inout float4 pos, float4 color = 0)
{
	float4 s = StereoParams.Load(0);

	if (is_hud_depth_pass()) {
		handle_hud_depth_pass(pos, color);
		return;
	}

	// If the loading screen icon is visible we don't adjust the HUD at all:
	if (loading_screen_preset)
		return;

	if (is_in_world_hud()) {
		handle_in_world_hud(pos);
		return;
	}

	// Return all HUD items to screen depth:
	if (pos.w != 1)
		pos.x -= s.x * (pos.w - s.y);

	// If the cursor is visible we are in a menu, keep it simple and leave
	// the whole HUD at screen depth so the mouse cursor lines up:
	if (cursor_showing)
		return;

	// Blacklist inventory circles at bottom of screen, since they overlap
	// with the mask. The actual icons are on a separate shader that does
	// not allow_crosshair_adjust to keep them at screen depth - if we
	// later need that shader auto-adjusted, we will need to change this to
	// a Y > -0.84 threshold check instead.
	//if (texture_filter == screen_depth_texture)
	//	return;
	// Battery swap icons need to be adjusted (or the text around them
	// unadjusted), so now switching to Y cutoff:
	if ((pos.y < hud_y_cutoff) && (abs(pos.x) < hud_x_cutoff))
		return;

	if (texture_filter == crosshair_texture && !crosshair_visible) {
		pos = 0;
		return;
	}

	// If full-screen HUD is displayed we disable all HUD adjustments this
	// frame. Necessary to disable all to avoid breaking text on loading
	// screen.
	if (is_fullscreen(pos))
		return;

	// Otherwise, adjust to crosshair depth if allowed for this shader:
	pos.x += adjust_from_depth_buffer(0, 0);
}
