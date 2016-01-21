The Forest
==========

Installation Instructions
-------------------------
1. Extract the zip file to the game directory
2. Turn off motion blur (the game doesn't currently save settings, so you have
   to do this every time)

Fixed
-----
- Halos on all surfaces
- Light, shadows and specular highlights
- Water
- Terrain = "High (Parallax Occlusion)" now makes the ground more 3D! Check out
  the sand, pebbles, etc.
- Certain UI elements that were originally drawn at screen depth (e.g. camp &
  build HUD icons) are now auto-adjusted (each vertex is adjusted
  independently, which may cause these to stretch similar to compatibility mode
  UIs). Note that most of the UI was already at a good depth in this game out
  of the box and has not been adjusted.
- Light shafts
- Glow around sun
- SSAO artefacts on rocky surfaces

Convergence Presets
-------------------
- [: (Default) Sets a good convergence for most of the game (0.4) with the
  crafting book pretty close to the mouse cursor.
- ]: Sets a higher convergence (2.5) that will bring the inventory closer to
  the mouse cursor.
- ~: Toggle the above two presets (I reassigned the inventory key to tab)

You can save your own custom convergence & separation preset to these buttons.
First, press the button you want to edit, then adjust the convergence and
separation with the standard nVidia keys (Ctrl+F5/F6 if advanced keys are
enabled in the control panel) and finally press F7 to save.

Known Issues
------------
- Mouse cursor is at screen depth
- Shadows do not fall quite right on parallax occluded terrain - they are
  slightly under the surface (they are in fact on the real surface, the 3D
  effect on the terrain could be considered an optical illusion).
- The Ceto Ocean system is partially broken due to a conflict with Helix Mod.
  Waves may behave a little strangely but it has no impact on gameplay.

Notes
-----
This is an early access game with regular updates, and as such the fix may get
Broken by an update. Please let me know if you see any issues after an update.
