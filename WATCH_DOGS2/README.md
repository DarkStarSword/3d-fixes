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
- Decals
- Skybox
- Light flares
- Volumetric Fog
- Water refraction
- Added an automatic stereo crosshair
- Added an automatic/manual crosshair toggle
- Minimap pinned at screen depth
- Profile dialogs capped no closer than screen depth
- Synchronised particle physics between eyes (for falling leaves - press F1 if
  they are still broken)
- Fixed the "strange blue glitch" at light volume boundaries
- Targetting lines
- Lighting on walls in nethack vision
- Glass panels in nethack vision

Installation
------------
1. Extract the zip file under WATCH_DOGS2\bin

2. Configure the settings:
   - Temporal Filtering: Off
   - Multisample Anti-Aliasing: Off

Keys
----
- K: Cycle between three crosshair modes: auto (enabled only when aiming), on
  and off.

- ~: Toggle between two convergence presets for cutscenes and gameplay.

- F1: Disable leaf particles (use if they are only visible in one eye or are in
  different positions in each eye)

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

Known Issues
------------
- Thick fog that occasionally rolls in over the bay is clipping incorrectly
- Screen space reflections are broken with temporal filtering (single GPU?):
  looks like a mono depth buffer needs steroising.

To Investigate
--------------
- Reports of flickering HUD on some systems after 10 minutes
- Leaves still only displaying in one eye for some people
- Reports of strange weather and disappearing objects (possible occlusion culling issue?):
  https://forums.geforce.com/default/topic/979185/3d-vision/watch-dogs-2-3d-vision/post/5047888/#5047888
