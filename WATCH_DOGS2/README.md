WATCH_DOGS 2
============

Fixed
-----
- Flickering HUD (render target redirection to work around game + driver bug)
- Accurate Screen Space Reflections (first ever accurate SSR fix for 3D Vision!)
- Accurate Specular Highlights
- Environmental reflections
- Some 2D objects in reflections
- Lights
- Regular Shadows
- PCSS Shadows
- HFTS Shadows
- HBAO+ Normal Map Artefacts
- Decals
- Skybox
- Light flares
- Volumetric Fog
- Water refraction
- Added an automatic stereo crosshair
- Added an automatic/manual crosshair toggle
- Added a static HUD depth adjustment
- Minimap pinned at screen depth
- Profile dialogs capped no closer than screen depth
- Work in progress to synchronise falling leaves between each eye (see below)
- Fixed the "strange blue glitch" at light volume boundaries
- Targetting lines
- Lighting on walls in nethack vision
- Glass panels in nethack vision

Installation
------------
1. Extract the zip file under WATCH_DOGS2\bin

2. Launch the game. The first time you run it (and again after any driver
   update) you will get a UAC prompt for Rundll32 to install the driver
   profile - choose yes.

The game has mostly been tested using the 376.33 driver. It may work on others,
but if you run into problems, try that driver first.

Keys
----
- K: Cycle between three crosshair modes: auto (enabled only when aiming), on
  and off.

- ~: Toggle between two convergence presets for cutscenes and gameplay.

- F1: Toggle leaf particles (disable if they are only visible in one eye or are
  in different positions in each eye)

- F2: Cycle between several preset HUD depths

Note about anti-cheat software
------------------------------
This game uses anti-cheat software that is running even while in single player.

As far as we know our 3D fixes have never triggered a ban with these type of
services, but if you play with it enabled you do so at your own risk.

If you want to be on the safe side you can disable it by launching the game
with the -eac_launcher option. If you are launching through UPlay you can go
into the properties page for the game and use "Add launch arguments" to add
this. If done correctly you will get a message when the game launches that the
anti cheat software is not installed and multiplayer will be unavailable.

HUD Depth
---------
To change the depth of the HUD, edit the d3dx.ini and change the value for x in
the [Constants] section. 0 is screen depth, 1 is infinity, negative numbers pop
out. You can also specify several preset values to cycle between with the F2
key by editing the [KeyHUDDepth] section.

There are also separate adjustments for 3D HUD elements in y and z, but these
are automatically biased to line up with the 2D HUD and you generally should
not need to adjust them separately.

Note that the HUD will always return to screen depth whenever the mouse cursor
is visible.

Falling Leaves
--------------
The falling leaves get out of sync between each eye in this game. I have a lot
of progress towards keeping them synchronised, but they still misbehave in some
cases, so I have disabled them by default. You can press F1 to toggle these on
and off, or edit the d3dx.ini and change x2 to 0 to enable them by default.

Known Issues
------------
- Thick fog that occasionally rolls in over the bay is clipping incorrectly
- Some fog is slightly uneven between each eye
- Fog glow around the sun / moon is at screen depth under certain weather
  conditions.

Side-by-Side / Top-and-Bottom Output Modes
------------------------------------------
This fix is bundled with the new SBS / TAB output mode support in 3DMigoto. To
enable it, edit the d3dx.ini, find the [Present] section and uncomment (remove
the semicolon) the line that reads:

    run = CustomShader3DVision2SBS

Then, in game press F11 to cycle output modes. If using 3D TV Play, set the
nvidia control panel to output checkerboard to remove the 720p limitation.

Like my Work?
-------------
Modding games takes a lot of time and effort, not to mention the work I do
behind the scenes improving our tools and helping others. If you like what I
do, consider supporting me on [Patreon](https://www.patreon.com/DarkStarSword)
for a recurring donation or [Paypal](https://www.paypal.me/DarkStarSword) for a
one off.

_This mod is created with 3DMigoto (by Bo3b, Chiri & myself) and uses Flugan's
assembler_
