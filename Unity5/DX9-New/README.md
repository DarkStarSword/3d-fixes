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

- Almost all halo issues in vertex shaders (some of these relate to the
  lighting)
- All lighting pixel shaders, including all known 3rd party replacement Unity
  lighting shaders.
- World space camera position in both vertex and pixel shaders

This script will also add sections to the DX9Settings.ini as it fixes shaders.
In particular it will add:

- Sections to copy the MVP and \_Object2World matrices from any shaders that
  were found to have them during the world space camera position fix, provided
  that it is not a shadow caster (you may need to add additional shaders if
  this is not sufficient - see below).

- Sections to copy the MVP and \_Object2World matrices to any shader that needs
  them for either a lighting fix and/or a world space camera position fix.

- Sections to use alternate stereo samplers for shaders that were already using
  the Helix Mod defaults (BUT BEWARE: Helix Mod doesn't unbind samplers, and
  this can lead to situations where a shader will be broken by Helix Mod even
  if it is not used in the fix. Ceto Water famously suffers from this problem
  in DX9 Unity games, and the only option may be to adjust the script to use a
  different default stereo sampler that doesn't break it, or at least doesn't
  break it quite as badly)

Unity likes to throw curve balls, so expect the unexpected. You may have to
adjust the script for the given game (check out the versions in The Forest and
Stranded Deep for ways to deal with Ceto water), and may need to edit some
shaders by hand.

If you find that the shadows are still broken after applying this template and
running the scripts, the most likely explanation is that none of the shaders
that the script added to copy the matrices from are in use. In that case use
the find\_more\_shaders.sh script to search for additional shaders with the
required matrices. It will call out to shadertool.py to install them and will
add the required sections to the DX9Settings.ini. Later I may update shadertool
to do this step for you.

UI adjustments are very game specific and as such are not included in the
template. shadertool will add sections to the DX9Settings.ini to copy the depth
buffer and Z Buffer params from various shaders to ease the process of adding
an automatic depth adjustment.
