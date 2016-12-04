Metal Gear Solid V: The Phantom Pain
====================================

Update v1.6
-----------
- Updated to 3DMigoto 1.2.50
- The driver profile is now updated automatically on launch, meaning extra high
  Ambient Occlusion will just work, and Compatibility Mode will automatically
  be disabled. You may get a UAC prompt the first time you run the game.

Update v1.5
-----------
- Fixed a crash that affects systems running the Windows 10 anniversary update.

Update v1.4
-----------
- Re-fixed red dot sight
- Unbroke targetting arc when throwing items
- Updated 3DMigoto to 1.2.40

Update v1.3
-----------
- Fixed several more shadows
- Partially fixed MGO, but some lights are still broken in most maps. NOTE:
  like any multi-player game, your use of this fix or any other mod with MGO is
  at your own risk.
- Bundled with latest 3DMigoto to enable SBS/TAB output modes (uncomment the
  'run = CustomShader3DVision2SBS' line to enable then press F11 in game to
  cycle output modes).

Update v1.2
-----------
- Fixed several more shadows, specular highlights & reflections
- Fixed atmospheric haze misalignment when camera is tilted
- Fixed flickering heat distortion through binoculars

Update v1.1
-----------
- Fixed atmospheric glow / fog
- Added an auto adjustment to the red dot sight like the crosshair
- Lowered the binoculars convergence preset a little

Fixed
-----
- Lights
- Shadows
- Specular Highlights (accurate!)
- Inverted mirrors
- Lens flares
- Decals
- Targetting circle when throwing items
- Water Reflections
- Moon pushed to infinity
- Auto-crosshair + red dot sight added
- 2D HUD moved to fixed depth (customise with x under [Constants])
- 3D HUD items moved closer to screen
- Atmospheric glow
- Heat distortion

Installation
------------
1. Extract the contents of the zip file to the game directory

2. Launch the game. The first time you run it (and again after any driver
   update) you will get a UAC prompt for Rundll32 to install the driver
   profile - choose yes.

3. Change the graphics settings to use exclusive full screen

Convergence Presets
-------------------
A number of convergence presets are added for convenience:

- I: Low preset for cinematics
- O: Moderate preset for gameplay
- P: High preset for gameplay
- {: High preset for horseback riding
- }: Extra high preset for horseback riding
- F / right shoulder (hold): Extremely high preset for binoculars
- F / right shoulder (tap while aiming): Very low preset for 1st person aiming

Note that holding down aim will also activate a convergence preset (same as O).
This is only so that the original convergence will be restored when you release
aim if you enter 1st person view.

All these presets can be customised by editing the d3dx.ini.

Side-by-Side / Top-and-Bottom Output Modes
------------------------------------------
This fix is bundled with the new SBS / TAB output mode support in 3DMigoto. To
enable it, edit the d3dx.ini, find the [Present] section and uncomment the line
that reads:

    run = CustomShader3DVision2SBS

Then, in game press F11 to cycle output modes. If using 3D TV Play, set the
nvidia control panel to output checkerboard to remove the 720p limitation.

Known Issues
------------
- Blue highlight on enemies behind cover is broken around the hips and
  disabled. Press F3 to re-enable.

Like my Work?
-------------
Consider supporting me on [Patreon](https://www.patreon.com/DarkStarSword)
