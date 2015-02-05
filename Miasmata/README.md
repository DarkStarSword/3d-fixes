Miasmata
========
This is a small improvement on [3D4DD's Miasmata Fix][1]. This is one of my
favourite games of all time and I have also released an [unofficial community
patch][2], [achievement tracker][3], [modding tool][4], and [French translation
with Gooby][5] ([github repository][6] for all of these).

While the 3D in this game is near-perfect with 3D4DD's fix, every now and again
I go back to see if I can make any improvements.

[1]: http://helixmod.blogspot.com.au/2012/12/miasmata.html
[2]: http://steamcommunity.com/app/223510/discussions/0/648812916771880184/
[3]: http://steamcommunity.com/app/223510/discussions/0/648813728501354813/
[4]: http://steamcommunity.com/app/223510/discussions/0/630800445647188169/
[5]: http://steamcommunity.com/app/223510/discussions/0/540741859566627042/
[6]: https://github.com/DarkStarSword/miasmata-fixes

Improvements
------------
- Fixes water such that it is no longer necessary to switch to the Aion
  profile.
- Medium/high quality water fixed with accurate real-time reflections.
- Update to latest Helix Mod.
- Move sky depth to infinity, such that it no longer varies with convergence.
- Fixed alignment issue between the water and sky at the horizon (medium & high
  quality water only).
- Fixed light shafts.
- Added an automatic stereo crosshair

Known Issues
------------
- Triangulation can be falsely obscured by an object to the left of the
  landmark while in 3D... I suspect this may be related to a haloing issue
  since it is obscured by the same offset that the water used to be broken by.
- Low quality water settings have issues near the edge of the map, visible on
  the horizon. Use medium or high quality water instead.
- **RESTART THE GAME AFTER CHANGING ANY GRAPHICS SETTINGS**

Installation
------------
- If you have assigned Miasmata to the Aion profile for the previous version of
  this fix, remove it from that profile.
- Unpack the zip file to the game directory, e.g.

    ...\Steam\SteamApps\common\Miasmata

- Recommended: Install the [unofficial communtiy patch][2]
- Set water quality to high to enable real-time 3D reflections
- Set Antialiasing to high (makes a huge difference to the water quality)
- **IMPORTANT: Restart the game** (do this any time you change any graphics quality settings)
