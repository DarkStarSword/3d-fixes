Far Cry Primal
==============

Update v1.1
-----------
- Updated to 3DMigoto 1.2.50
- Driver profile is automatically updated on launch.

Fixed
-----
- Volumetric fog completely and accurately fixed and looks awesome in 3D :)
	- Shadow volumes (e.g. cast from trees)
	- Light volumes (e.g. in caves)
	- Camp fires
	- Density near mountains
	- Density near cliffs
	- Density in sky
- Specular highlights are fixed accurately!
- Lights / Shadows
	- Tile Lighting
	- Directional
	- Ambient
	- Physical
- Water reflections
	- Real reflections outdoors (using stereo reversal technique)
	- Environment map reflections in caves
- Ambient Occlusion
	- Normal map artefacts
	- Disabled false velocity smearing
- Auto crosshair added
- Enemy & animal tags
- Mask of Krati crystals around edge of screen moved to fixed depth
- Halos
- Lens flares
- Vignette pushed to depth
- Hunter vision yellow outline fade out at edge of screen lined up better
- Underwater caustics
- Decals
- Bloom

Installation
------------
1. Unpack the zip file to the Far Cry Primal\bin directory

2. Launch the game. The first time you run it (and again after any driver
   update) you will get a UAC prompt for Rundll32 to install the driver
   profile - choose yes.

3. Disable Motion Blur in the settings

4. If using SLI, lower the water quality slightly to drastically improve the framerate.

HUD Modes
---------
Two different automatic HUD modes are provided:

The default mode will adjust the entire HUD based on the center of the screen,
which is well suited to general gameplay so that the crosshair will line up
with the target.

The second mode will try to adjust the HUD to be mostly in front of anything on
the screen. This mode is intended for use in cutscenes to help make the
subtitles easier to read.

The ~ key can be used to toggle between both of these modes. If you would
prefer to use a fixed depth HUD, you can do so by editing the d3dx.ini - x2
sets the mode and x sets the fixed depth for mode 0.

Convergence Presets
-------------------
Press backslash to cycle between two convergence presets - a low preset
recommended for most of the game, and a high preset intended for use in the
Legend of the Mammoth DLC.

Side-by-Side / Top-and-Bottom Output Modes
------------------------------------------
This fix is bundled with the new SBS / TAB output mode support in 3DMigoto. To
enable it, edit the d3dx.ini, find the [Present] section and uncomment the line
that reads:

    run = CustomShader3DVision2SBS

Then, in game press F11 to cycle output modes. If using 3D TV Play, set the
nvidia control panel to output checkerboard to remove the 720p limitation.

Notes
-----
There are some reports that recent drivers are causing issues for some people.
If you have trouble, 361.91 and 362.00 are known to work for this game.

I may revisit the game later to improve the HUD like I did in FC4, but this is
quite playable as is.

Known Issues
------------
- Vignette underwater is not lined up with the edge of the screen (related to
  the HUD), but is a pretty minor issue.

- Some of the cutscenes have excessive sparkles at the far left of the screen.

- Some of the reflections are not accurate in 2D, and therefore not accurate in
  3D either. The river near the village is probably the worst for this as from
  certain camera angles plants can be seen stretched across the water. This is
  a game bug.

- If you use an unusual resolution, the fog in some areas (such as while
  obtaining the Owl guide) may be cut off the right of the screen. This occurs
  even in 2D and is a game bug. 1920x1080 and 1280x720 both work fine.

Like my Work?
-------------
Consider supporting me on [Patreon](https://www.patreon.com/DarkStarSword)

_This mod is created with 3DMigoto (by Bo3b, Chiri & myself) and uses Flugan's
assembler_
