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
- Added a 3D HUD depth bias
- Adjusted lens grit depth
- Work in progress to synchronise falling leaves between each eye (see below)
- Fixed the "strange blue glitch" at light volume boundaries
- Targetting lines
- Lighting on walls in nethack vision
- Glass panels in nethack vision
- Partial fix for NVIDIA Ansel mode (likely still broken in many areas)

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

- \: Toggle leaf particles (disable if they are only visible in one eye or are
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
To change the depth of the 2D HUD, edit the d3dx.ini and change the value for x
and y in the [Constants] section - x sets the depth when the mouse cursor is
NOT visible, and y sets it when the mouse cursor IS visible. 0 is screen depth,
1 is infinity, negative numbers pop out. You can also specify several preset
values to cycle between with the F2 key by editing the [KeyHUDDepth] section.

There are also separate adjustments for 3D HUD elements in z and w. The units
are convergence override values, so higher values bring the HUD closer and
lower values push it deeper (0 is infinity). z sets the convergence override
when the mouse cursor is hidden, and this adjustment will also have a bias
applied to line it up with any 2D HUD adjustments. w sets the 3D HUD
convergence override when the mouse cursor is hidden, and does NOT have a bias
(the idea being that when the mouse cursor is visible you want the HUD near
screen depth where the mouse cursor is).

Lens Grit
---------
The lens grit texture has been moved to depth to look better. The depth can be
adjusted with y2 in the d3dx.ini, or disabled by setting y2 = -1.

Falling Leaves
--------------
The falling leaves get out of sync between each eye in this game. I have a lot
of progress towards keeping them synchronised, but they still misbehave in some
cases, so I have disabled them by default. You can press F1 to toggle these on
and off, or edit the d3dx.ini and change x2 to 0 to enable them by default.

Known Issues
------------
- Fog from steam vents is uneven between each eye (conflict with other parts of
  the volumetric fog fix)
- Thick fog that occasionally rolls in over the bay is clipping incorrectly
- Some other fog is slightly uneven between each eye
- Fog glow around the sun / moon is at screen depth under certain weather
  conditions.
- Police search lights clip momentarily as the camera passes through the
  boundary of the light cone.

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
