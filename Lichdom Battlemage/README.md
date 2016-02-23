Lichdom: Battlemage
===================

Fixed
-----
- **First ever CryEngine 3 Shadow fix!!!**
- Forced nVidia 3D Vision Automatic mode
- Unlocked separation
- "Pulsating" translucent effects
- Disappearing / flickering objects
- Specular highlights
- Environmental reflections
- Decals
- Light shafts
- Skybox (starfield, moon, moon glow, lightning glow)
- Water & reflections
- Halos on all surfaces
- Clipping on certain shadows and wet rocks

Installation
------------
1. Extract zip file to game directory. If done correctly there should be a
   d3d11.dll in both the Bin32 and Bin64 directories.

2. Launch the game. If 3D does not engage, press alt+enter to change full
   screen modes

3. Press backslash to load the recommended convergence preset, and adjust as
   desired.

Damage indicators
-----------------
Press x to move the UI in the top half of the screen to depth to make damage
indicators comfortable to see. This will break the menus, so press x again to
return the UI to screen depth.

Troubleshooting
---------------
- If the 3D does not engage, try pressing alt+enter. If that doesn't work,
  change the screen mode to windowed then back to full screen.

- If you notice the UI adjustment only partially works (i.e. text pushed back,
  but the background remains at screen depth), change the resolution and then
  change it back.

- Some Windows 8.1 users may have to use the 32bit version of the game.

- If your framerate is abnormally low, try changing the resolution and then
  changing it back.

- If the framerate is abnormally low only when facing certain directions you
  may be able to regain some fps at the cost of objects disappearing when they
  shouldn't. Edit the d3dx.ini and change deny_cpu_read to 0 at the bottom. You
  can edit this while the game is running - press F10 to reload the config.

- Driver bugs can cause numerous rendering issues after playing for a while. If
  you see a stuck image, moving shadows, one eye brighter than the other, the
  whole screen blanking out, or some other weird glitch it's a sign you should
  probably save and restart the game soon. Disabling the shader cache in the
  control panel may help.

- If you find a broken effect please let me know where to find it. Be sure to
  mention what graphics settings you are using (especially water and "visual
  quality"). For reference, I have most settings set to either High or Very
  High.

*Special thanks to Flugan for his work on the assembler, used in this fix.*
