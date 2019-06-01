Team Sonic Racing
=================

Fixes
-----
- Lighting halos
- Various transparent effect halos
- Shadows
- Accurate specular reflections (fantastic!)
- Ambient Occlusion artefacts
- Ambient Occlusion game bug!
- Automatic eye swap during mirror mode tracks
- Adjusts HUD depth while driving
- Hides mouse cursor
- Fog

Installation
------------
Extract the contents of the zip file to the game directory.

HUD Adjustment
--------------
The HUD will automatically adjust itself while holding down the accelerator key
during a match (left shift or right trigger). If you use a non-standard
accelerator button change the binding under [KeyAccelerateController] in the
d3dx.ini. You can also tweak the HUD depth under [Constants] and the timings
under the above key binding.

Ambient Occlusion Bug Fix
-------------------------
This fix corrects a game bug which could cause shadow artefacts, however this
fix changes the tone of some of the graphics. If you would prefer to play with
the vanilla tone and accept the artefacts, Ctrl+Shift+Alt+B will toggle the AO
BUG fix on and off.

Mouse Cursor
------------
This fix hides the mouse cursor, on the assumption that you are playing with a
controller. If you prefer to use the mouse to navigate the menus change
hide_cursor to 0 in the d3dx.ini.

Game Settings
-------------
Although I have fixed issues on low quality settings and it should work, I've
mostly been playing on high quality settings, so if you see any stereo issues
try setting the quality to high first.

Screenshots
-----------
The controller back button will take a 3D screenshot that can be found in the
usual Documents\NVStereoscopic3D.IMG place.

Side-by-Side / Top-and-Bottom Output Modes (3D Vision Users Only)
-----------------------------------------------------------------
This fix is bundled with the SBS / TAB output mode support in 3DMigoto. To
enable it, edit the d3dx.ini, find the [Include] section and uncomment (remove
the semicolon) the line that reads:

    include = ShaderFixes\3dvision2sbs.ini

Then, in game press F11 to cycle output modes. If using 3D TV Play, set the
nvidia control panel to output checkerboard to remove the 720p limitation.

Like my Work?
-------------
Fixing games takes a lot of time and effort, and I also do a lot of work on
3DMigoto behind the scenes to make all of these mods possible - in particular,
this release required writing an entirely new loader mechanism for 3DMigoto as
well as solving a lot of hangs and crashes.

If you are in a position where you are able to do so, please consider
[supporting me with a monthly donation on Patreon][1], and thanks again to
those that already do! While I prefer the more stable monthly support that
Patreon offers, I can of course understand that some of you prefer to make
one-off donations when you can, and for that you can use [my Paypal][2]. As a
reminder, these donations are to support me personally, and do not go to other
modders on this site.

[1]: https://www.patreon.com/DarkStarSword
[2]: https://www.paypal.me/DarkStarSword

_This mod is created with 3DMigoto (primarily written by myself, Bo3b and
Chiri), and uses Flugan's Assembler. See [here][4] for a full list of
contributors to 3DMigoto_

[4]: https://darkstarsword.net/3Dmigoto-stats/authors.html
