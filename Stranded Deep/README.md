Stranded Deep
=============

Fixed
-----
- Halos
- Water refraction
- Underwater shadows
- Moved highlights on ocean floor to correct depth
- Sun shafts
- Underwater crepuscular rays
- Automatically remove the crosshair when it is faded out

Installation
------------
1. Extract the zip file to the game directory

    ...\Steam\SteamApps\common\Stranded Deep

2. If your Stranded Deep executable is named Stranded_Deep_x86.exe (as opposed
   to Stranded_Deep_x64.exe), replace the d3d9.dll from the fix with the one in
   the 32bit directory.

3. Launch the game and set quality to Ultra (other settings may work as well,
   but I haven't tested them)

Keys
----
- L: Activate recommended convergence preset - use after starting a new game,
  loading an existing game or alt+tabbing. A custom convergence can be saved
  on this key by pressing L, adjusting the convergence, then pressing F7.

- F: Holding sets a convergence suitable for use with the watch, and will
  return to the L preset on release.

- X: Cycles between four four HUD depth presets - 75% (default), 99.5%, screen
  depth and 50%.

- V: Cycles crosshair modes between automatic, always enabled and always
  disabled (crosshair must be enabled in the settings).

Troubleshooting
---------------
- If the water looks broken, try alt+tabbing out of the game and back in.

- The convergence gets reset after starting or loading a game - press L to load
  the recommended convergence preset.

Known Issues
------------
- Mouse cursor depth cannot be adjusted

- From above, the waves right on the edge of the shore only move the water in
  one eye.

Notes
-----
- This is an early access game and the fix is likely to be broken by updates,
  so be sure to check back regularly, and report any broken effects.

- This game has pushed DirectX9 shaders right to their limits, which caused me
  some problems creating the fix. Everything seems to be working now, but
  please let me know if you notice any details on the terrain or Ocean that are
  missing with the fix installed (such as missing shadows on the sand).
