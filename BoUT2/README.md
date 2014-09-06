The Book of Unwritten Tales 2
==============================

Fixed
-----
- Disables broken shadows (can be toggled on and off with 7)
- Can push subtitles to 75% depth by pressing 9, though this causes text in the
  menus to move to the right.

Known Issues
------------
- Adjusting separation with Ctrl+F3/F4 causes game to crash
- Adjusting convergence with Ctrl+F5/F6 causes further mouse clicks to be
  ignored, requiring the game to be restarted to make any meaningful progress.
- Mouse cursor is stuck at screen depth and I can find neither a vertex nor
  pixel shader to adjust it.
- Reflections are broken


Notes
-----
This game changes it's working directory after launch, which complicates
matters in terms of what goes where.

DX9settings.ini and ShaderOverrides need to go under here:

    The Book of Unwritten Tales 2

d3d9.dll goes here:

    The Book of Unwritten Tales 2\Windows

The debug dll may dump shaders under Windows\Dumps or just Dumps depending on
how you launched the game. It might also put the AllShaders in a different
location to the SingleShaders.
