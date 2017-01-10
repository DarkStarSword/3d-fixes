WATCH_DOGS 2
============

Update v1.2
-----------
- Fixed several crossairs: Sniper scope, Grenade launcher, X hit indicator, red crosshairs
- Moved bullets and Police sniper laser back to 3D (was caught by a HUD adjustment)
- Fixed a few minor issues on the horizon & around sun

Update v1.1
-----------
- Fixed clipping on thick San Francisco volumetric fog
- Fixed another type of fog - should make fog 3D under all weather conditions
- Fixed more instances of 2D transparent effects in nethack vision (glass
  panels on the Temple of New Dawn glass & shrink wrap)
- Fixed wrong reflections on some hair
- Fixed blood decals
- Fixed brick decals floating a few milimeters above pavement with shadows
  falling through them.
- Added shotgun crosshair to auto adjust list
- Fixed glow of sun/moon when viewed through the thick San Francisco fog
- Fixed steam explosions

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
- Police Helicopter Searchlight
- Water refraction
- Added an automatic stereo crosshair
- Added an automatic/manual crosshair toggle
- Added a static HUD depth adjustment
- Added a 3D HUD depth bias
- Adjusted lens grit depth
- Synchronised leaves, grass, bushes, etc. between both eyes (if the leaves
  ever manage to get out of sync you can disable them by pressing backslash)
- Fixed the "strange blue glitch" at light volume boundaries
- Targetting lines
- Lighting on walls in nethack vision
- Glass panels in nethack vision
- "Fake" building interiors (lights through windows render at correct depth)
- Partial fix for NVIDIA Ansel mode (see below)

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

NVIDIA Ansel Mode
-----------------
This is one of the games supported by NVIDIA Ansel, which allows you to
position the camera, adjust the FOV, etc. and take various types of
screenshots. Press Alt+F2 in game to pause the game and bring up Ansel HUD,
then move the camera with WASD, Z, X and rotate by holding the left mouse
button and use the HUD to adjust other controls.

The various screenshot options provided by Ansel should all work fine, but
personally I find the stereo screenshot option to be lacking (no off-center
projection and very little depth), but you can just use it to position the
camera then take a stereo screenshot with Alt+F1 (beware the 100 screenshot
limit if you aren't using my auto rename script).

To remove the Ansel HUD for better screenshots in this mode, open the d3dx.ini,
search for "Ansel" and uncomment the two ShaderOverride sections. Back in game
press F10 to reload the config and voila - no HUD :) Note that the various
filters Ansel provides only work in one eye in this game.

Note that there are very likely still broken effects (especially lights,
shadows and reflections) while using Ansel in many areas / times of day /
weather conditions - I've fixed a bunch of them, but they only dump on demand
when Ansel is used, so finding them all is a near impossible task. You can
still use Ansel's stereo screenshot option if there are broken shaders.

Known Issues
------------
- Fog from steam vents is falsely obscured when an object is in front of them,
  which can lead to be being shaded differently in each eye. This is a game bug
  that occurs in 2D as well.
- Police search lights clip momentarily as the camera passes through the
  boundary of the light cone. Probably only noticeable if you freeze the game
  with Ansel.

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
