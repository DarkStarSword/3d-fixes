Montague's Mount
================

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
- Added two convergence presets on [ and ] keys for convienience.

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
- The HUD depth can be customised with the keys on the number row, and tilde to
  return to screen depth.
- Two convergence presets are provided on the [ and ] keys for convienience.
- If the FOV is set very high the lens flare may look a bit off when it is near
  the side of the screen.
- If you see rendering issues in the game, try pressing [, or adjusting the
  separation or convergence or alt+tabbing out and in of the game. This doesn't
  seem to happen for me anymore, so it may have been related to the profile
  used in previous versions of the fix.
