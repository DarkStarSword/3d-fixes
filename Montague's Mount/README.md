Montague's Mount
================

Update v3:
----------
- Fixed bloom around lights once electricity has been turned on
- Approximate fix for interior and spot light shadows
- Inventory text depth fixed

Update v2:
----------
- Shadows fixed thanks to 4everAwake
- Lens flare fixed
- Switched to use the Harry Potter profile by default, which seems a little
  more stable than the Aion profile (still sometimes see flickering - alt+tab
  out and in until it goes away).

**RECOMMENDED: Use nVidia Inspector to assign this game to the "Harry Potter -
Deathly Hollows Part1" profile.** The game will try to use this profile
automatically, but it doesn't always work (and can randomly stop working) -
much better to manually assign it with nVidia inspector.

**If the shadows are broken or you are seeing severe flickering or haloing on
some surfaces try alt+tabbing out and in of the game (you may need to try
several times)** - both Helix mod and the driver profile seem to be really
inconsistent with this game.

Do not change the FOV from the default value of 65 - I realise that is lower
than some people would like, but the shadow fix would have to be recalibrated
for different FOV settings. I wasn't able to get shadows from interior lights
to line up perfectly at all distances from the camera, so I chose the best
value I could for each. Exterior shadows don't have this issue.

The HUD depth can be customised with the keys on the number row, and tilde to
return to screen depth.

Troubleshooting
---------------
For some reason Helix mod doesn't always engage when launching the game, (easy
to tell as the shadows will be broken and the HUD depth customisation won't
work) - try disabling and enabling 3D or alt+tabbing out and in until it works.

If you get flickering on some surfaces like the grass, try alt+tabbing out and
in a few times until it stops *and* the shadows look right (may take a few
attempts). Make sure the game is assigned to the Harry Potter profile and not
Aion, since the Harry Potter profile seems to be a bit more reliable.
