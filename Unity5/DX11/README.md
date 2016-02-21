Unity 5 World Space Correction Template
=======================================

**THIS TEMPLATE WILL NOT WORK WITH UNITY 5.3 WITHOUT CONSIDERABLE EFFORT PENDING UPDATES TO THE EXTRACTION SCRIPTS**

This template can be used as a starting point to fix any DX11 Unity game. It
includes:

- d3dx.ini excerpts
- Lighting vertex shaders

The vast majority of the fix is now performed with hlsltool.py. autofix.sh is
a shell script that can be run from cygwin (or any other Unix environment) to
perform these fixes automatically. It will fix:

- Almost all halo issues in vertex shaders (some of these relate to the
  lighting)
- All lighting pixel shaders, including all known 3rd party replacement Unity
  lighting shaders.
- World space camera position in both vertex and pixel shaders

This script will also add sections to the d3dx.ini as it fixes shaders.  In
particular it will add:

- Sections to copy the MVP and \_Object2World matrices from any shaders that
  were found to have them during the world space camera position fix, provided
  that it is not a shadow caster (you may need to add additional shaders if
  this is not sufficient - see below).

- Sections to copy the MVP and \_Object2World matrices to any shader that needs
  them for either a lighting fix and/or a world space camera position fix.

Unity likes to throw curve balls, so expect the unexpected. You may have to
adjust the script for the given game, and may need to edit some shaders by
hand. This script is subject to the 3DMigoto decompiler, so you may have to
hand-edit some shaders to fix decompile bugs, but these are generally minor.
Any that fail a compile test will have ~failed appended to their filename.

If you find that the shadows are still broken after applying this template and
running the scripts, the most likely explanation is that none of the shaders
that the script added to copy the matrices from are in use. There is a script
in the DX9 template that can find more shaders that could be adapted to work
with DX11 relatively easily.

UI adjustments are very game specific and as such are not included in the
template. hlsltool will add sections to the d3dx.ini to copy the depth buffer
and Z Buffer params from various shaders to ease the process of adding an
automatic depth adjustment.
