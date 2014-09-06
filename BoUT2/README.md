The Book of Unwritten Tales 2
==============================

- Disables broken shadows (can be toggled on and off with 7)

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
