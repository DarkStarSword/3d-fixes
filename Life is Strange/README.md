Life is Strange
===============

Update 2015-10-21
-----------------
- Fixed Episode 5
- Added approximate fix for bloom around lights using depth buffer (press H to
  move them to infinite depth instead)

Update 2015-08-16
-----------------
- Fixed Episode 4

Update 2015-05-24
-----------------
- Fixed Episode 3
- Fixed some more lighting effects

Update 2015-03-25
-----------------
- Fixed Episode 2
- Disable some fog effects that broke with SkipSetScissorRect (Press P to
  re-enable this)

Update 2015-02-01
-----------------
- Added subtitle depth adjustment (see below)

Fixed
-----
- Halos
- Fog
- Shadows
- Glow around sun
- Approximate fix for bloom around lights (Press H to change to an alternate
  adjustment that places these at infinity)
- Light shafts
- Reflections on ground
- Clipping on decals
- Convergence is increased to 50.0 by default. To save a custom setting, press
  plus on the number row before adjusting the convergence, then press F7 to
  save.

Installation
------------
Unpack the zip file under:

    ...\Steam\SteamApps\common\Life Is Strange\Binaries\Win32

Subtitle Depth Adjustment
-------------------------
I recommend disabling the subtitles in the settings, but if you prefer to play
with them enabled you may adjust their depth with the keys on the number row.
This adjusts the subtitles and menus, but can cause in-world HUD elements to
flicker momentarily when at a certain distance from the camera, so it is
disabled by default. tilde sets screen depth, 0 sets 99.5% and 1-9 sets
anywhere between. Press minus on the number row to disable the adjustment and
return to the game's default depth.

Notes
-----
- I played on high quality and have not checked for issues on lower settings.

Like my Work?
-------------
Consider supporting me on [Patreon](https://www.patreon.com/DarkStarSword)
