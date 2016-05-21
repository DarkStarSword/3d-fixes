Stranded Deep
=============

Update 2015-05-22
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

3. Select "Play Stranded Deep with DirectX 11.0" when launching the game from
   Steam (if you previously added any launch options, remove them)

4. Press L to activate the recommended convergence preset.

Keys
----
- L: Activate recommended convergence preset.

- F: Holding sets a convergence suitable for use with the watch, and will
  return to the L preset on release.

- V: Cycles crosshair modes between automatic, always enabled and always
  disabled (crosshair must be enabled in the settings).

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
