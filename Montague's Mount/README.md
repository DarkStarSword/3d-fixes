Montague's Mount
================

Installation
------------
1. Extract the zip file under ...\Steam\SteamApps\common\Montague's Mount

2. **IMPORTANT: Open the DX9Settings.ini file and change the DepthForceWidth and
   DepthForceHeight lines to match the resolution you intend to play the game.**

   Skipping this step may result in missing shadows and the stereo crosshair
   not working!

Update v5 (2015-05-20)
----------------------
This update adds an automatic stereo crosshair, which replaces the manual UI
depth adjustment. Be sure to remove the old ShaderOverride folder before
installing, and **follow the new installation instructions**.

Update v4 (2014-12-16):
-----------------------
This is a major update that removes the need for the profile change, fixes
shadows correctly and can work with any FOV. If you have previously assigned
this game to the Aion or Harry Potter profiles with nVidia inspector, you
should remove it from any profiles it is in.

- Fixed all Unity surface shaders, removing the need for the profile change.
  This drastically improves the stability of the fix and should eliminate
  the flickering issues (except those present in 2D).
- Added my Unity lighting shader fix, which correctly fixes shadow alignment
  issues and will work with any FOV. This also fixes some lighting related
  rendering issues noticable in the water.
- Forced shadow maps to mono, which fixes some shadow alignment issues on the
  spot lights on the dock.
- Fixed minor halo in water near rocks
- Added two convergence presets on [ and ] keys for convenience.

I have checked most areas, but haven't replayed the entire game with this
update, so please let me know if you see any surfaces rendering incorrectly.

Update v3 (2014-10-18):
-----------------------
- Fixed halo around lights once electricity has been turned on
- Approximate fix for interior and spot light shadows
- Inventory text depth fixed

Update v2 (2014-10-16):
-----------------------
- Shadows fixed thanks to 4everAwake
- Lens flare fixed
- Switched to use the Harry Potter profile by default, which seems a little
  more stable than the Aion profile (still sometimes see flickering - alt+tab
  out and in until it goes away).

v1 (2014-10-14):
----------------
- Surfaces fixed by profile (unstable)
- Disabled shadows

Notes
-----
- Two convergence presets are provided on the [ and ] keys for convienience.
- If the FOV is set very high the lens flare may look a bit off when it is near
  the side of the screen.

Like my Work?
-------------
Consider supporting me on [Patreon](https://www.patreon.com/DarkStarSword)
