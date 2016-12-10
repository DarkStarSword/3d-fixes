Stranded Deep
=============

Update 2016-12-xx
-----------------
- Fix updated for version 0.19 of the game.
- Profile is installed on first launch to set the default convergence.
- Removed full screen override (as it has been fixed in the game/engine once
  again... hopefully they won't break it again).

Update 2016-07-18
-----------------
Fix is updated to work with version 0.14 of the game. The fix will now force
exclusive mode full screen since this was broken in the 0.14 update.

Update 2016-07-14
-----------------
The fix has been updated to work with the latest version of the game (0.13.H1).
This update switches many shaders to assembly to fix certain rendering issues -
**be sure to remove the old version of the fix with the provided uninstall.bat
before installing this version.**

Update 2016-05-22
-----------------
The entire fix has been redone from scratch after an engine update to Unity 5.3
completely broke the previous version of the fix along with my unity scripts
due to major changes to the shader file format in Unity.

This version also updates the fix to use DirectX11 - be sure to select it when
launching the game, and remove the -force-d3d9 launch option if you previously
added it.

Various issues with Ceto water have been fixed - the waves behave correctly
(calm near the shore, rough further out) and it no longer misalignes when the
the camera is tilted while side stepping.

The HUD depth adjustment now automatically disabled whenever the mouse cursor
is shown in a menu, removing the need to do this manually.

Fixed
-----
- Halos
- Water refraction
- Underwater shadows
- Moved highlights on ocean floor to correct depth
- Sun shafts
- Underwater crepuscular rays
- Automatically adjust the crosshair depth
- Automatically remove the crosshair when it is faded out
- HUD depth adjustment is disabled when in a menu.
- <strike>Parallax sand is now 3D</strike> Effect is not used in latest update
- SSAO artefacts on rocky surfaces
- Ocean misalignment when camera is tilted

Installation
------------
1. Extract the zip file to the game directory

    ...\Steam\SteamApps\common\Stranded Deep

2. If your Stranded Deep executable is named Stranded_Deep_x86.exe (as opposed
   to Stranded_Deep_x64.exe), replace the DLLs from the fix with those in the
   32bit directory.

3. Select "Play Stranded Deep with DirectX 11.0" and "Exclusive" full screen
   mode when launching the game from Steam (if you previously added any launch
   options, remove them)

4. The first time you launch the game (and again after any driver update) you
   will get a UAC prompt for Rundll32 to install the driver profile - choose
   yes.

Keys
----
- L: Activate recommended convergence preset.

- F: Holding sets a convergence suitable for use with the watch, and will
  return to the L preset on release.

- V: Cycles crosshair modes between automatic, always enabled and always
  disabled (crosshair must be enabled in the settings).

Known Issues
------------
- The vignette for damage / out of breath is misaligned.

Troubleshooting
---------------
If the game launches in the background and can't be restored try killing it
through task manager and trying again. If it continues to do this, try hitting
show desktop immediately after launching the game and before it's window has
appeared. You should then be able to restore the game. You may need to use
Alt+Enter to switch to full screen mode after this procedure.

Do not Alt+Tab out of the game as it will hang (a long standing Unity bug). If
you are desperate, use Alt+Enter to switch to windowed mode first, but note
that the game may be glitched after returning to it.

Notes
-----
- This is an early access game and the fix is likely to be broken by updates,
  so be sure to check back regularly, and report any broken effects.

Like my Work?
-------------
Consider supporting me on [Patreon](https://www.patreon.com/DarkStarSword)

_This mod is created with 3DMigoto (by Bo3b, Chiri & myself) and uses Flugan's
assembler_
