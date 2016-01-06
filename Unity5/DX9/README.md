Unity 5 View Space Correction Template
======================================

This template can be used as a starting point to fix any DX9 Unity game. It
includes:

- DX9Settings.ini with some common options, and directives to copy the required
  MV and MVP matrices from several common shaders (there is a good chance you
  may need to adjust this - see below)
- Point/Spot/Physical lighting vertex shader
- Directional lighting vertex shader
- A number of common lighting pixel shaders (there is a high chance that you
  will need to fix additional lighting shaders with shadertool - see below)
- Several vertex shaders with halo type issues that cannot be autofixed
- SSAO pixel shaders

A considerable portion of the fix is now performed with shadertool.py.
autofix.sh is a shell script that can be run from cygwin (or any other Unix
environment) to perform these fixes automatically. It will fix:

- Almost all halo issues in vertex shaders (some of these relate to the
  lighting)
- All lighting pixel shaders, including all known 3rd party replacement Unity
  lighting shaders.
- World space camera position in the deferred lighting shaders ONLY. This will
  fix things like specular highlights and environmental reflections, but will
  not fix all of them or other related problems. There is an alternative
  DX9-New template that can fix all of these.

Unity likes to throw curve balls, so expect the unexpected. You may have to
adjust the script for the given game (check out the versions in The Forest and
Stranded Deep for ways to deal with Ceto water), and may need to edit some
shaders by hand.

Depending on what lighting and other shaders the game uses you may need to make
adjustments to where the FOV is sourced from. In particular, if you notice that
shadows from point or spot lights are broken:

- If directional lighting is also in use the fix will copy the FOV from that to
  use in the point/spot/physical lighting shaders as it is usually reliable. On
  occasion however (Dreamfall Chapters Unity 5 update), this has proved not to
  be the case - in that case you should edit the DX9Settings.ini and comment
  out the [VS00933666] and [VS678DC18B] sections, which will cause it to always
  fall back to the Unity 4 techniques instead.

- If the Unity 4 techniques are in use (either because directional lighting is
  not being used by the game or you have disabled them in the DX9Settings.ini)
  the fix will instead use the MV and MVP matrices copied from other shaders.
  The template includes a couple of common particle vertex shaders that have
  these matrices, but it is likely that you will need to find additional
  shaders to copy them from, and you may also need to disable the particle
  shaders as they sometimes give bogus results (seems to be becoming more
  common in newer Unity versions).  
    
  The two matrices you are looking for are glstate\_matrix\_modelview0 (copy
  with GetMatrixFromReg) and glstate\_matrix\_mvp (copy with GetConst2FromReg).
  You should look in the shaders extracted from the game files with my tools as
  they extract the headers that are missing with shaders dumped from Helix Mod.
  It is vitally important that you only use shaders that draw an object in the
  3D world from the perspective of the camera - in particular avoid UI shaders
  or any that have names like camera depth or normal. Any that have
  "LIGHTMODE"="SHADOWCASTER" in their headers are a definite no-no.

- If you have no shaders to copy the required matrices from at all, you will
  either need to hardcode the FOV by adjusting c220.w in 05F7E52C.txt, or
  switch to the DX9-New template which uses a different set of matrices that
  are more widely available.

UI adjustments are very game specific and as such are not included in the
template.
