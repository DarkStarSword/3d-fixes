Unity 5 World Space Correction Template
=======================================

This template can be used as a starting point to fix any DX9 Unity game. It
includes:

- DX9Settings.ini with some common options
- Lighting vertex shader
- Several vertex shaders with halo type issues that cannot be autofixed
- SSAO pixel shaders

The vast majority of the fix is now performed with shadertool.py. autofix.sh is
a shell script that can be run from cygwin (or any other Unix environment) to
perform these fixes automatically. It will fix:

- Almost all halo issues in vertex shaders
- All lighting pixel shaders, including all known 3rd party replacement Unity
  lighting shaders.
- World space camera position in both vertex and pixel shaders

Unity likes to throw curve balls, so expect the unexpected. You may have to
adjust the script for the given game (check out the versions in The Forest and
Stranded Deep for ways to deal with Ceto water), and may need to edit some
shaders by hand.

UI adjustments are very game specific and as such are not included in the
template. shadertool will add sections to the DX9Settings.ini to copy the depth
buffer and Z Buffer params from various shaders to ease the process of adding
an automatic depth adjustment.
