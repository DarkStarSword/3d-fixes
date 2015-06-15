Unity
=====

This contains a fix for the Hidden/Internal-PrePassLighting and
Hidden/Internal-PrePassCollectShadows shaders that are responsible for the
broken shadows in many Unity games that use deferred rendering, with and
without cascading shadows.

Note that some of the variants of these shaders are only pre-emptively fixed -
that is, I have not necessarily actually seen them in use in a game to verify
the fix is correct, but that I assume the fix should work based on the other
variants that I have verified.

I originally developed this technique for fixing Unity shadows for Dreamfall
Chapters, however that game uses replacements for both of these internal
shaders (unitysunshine.com), so uses a different set of shaders to the ones
fixed here. Please refer to the [fix for that game][1] and the [corresponding
forum thread][2] for more details.

[1]: http://helixmod.blogspot.com/2014/11/dreamfall-chapters.html
[2]: https://forums.geforce.com/default/topic/781954/3d-vision/dreamfall-chapters

In addition to fixing the lighting shaders, *every* surface shader also needs
to be fixed. This is usually quite trivial as they simply copy the mono screen
coordinates in the vertex shader into a texcoord, which is used to transfer
lighting & shadows on to the surface in the pixel shader. Simply stereoising
this output is usually all that is needed to fix each surface shader, but there
are a *lot* of them to fix.

When shader hunting for surface shaders in Unity games with Helix Mod, a trick
is to look out for a surface turning into a solid colour with the vertex shader
disabled. If you aren't able to find the correct one, try disabling pixel
shaders until the broken surface changes to a solid colour, then use the number
next to PixelPair to identify the corresponding vertex shader.

builtin\_shaders
----------------
This contains an __experimental and incomplete__ fix to the Unity lighting
shader source code to work with Helix mod. This is only suitable for use for
games using the vanilla Unity lighting shader and the variantes of the compiled
result will need to be matched up with the original CRCs for replacement.

This is currently missing the fix to the Internal-PrePassCollectShadows shader
and the screen/directional variants of Internal-PrePassLighting.

Information for Developers
--------------------------
The files here are designed for use with Helix Mod to fix a game after the
fact. If you are developing a Unity game you are better off fixing the shaders
directly. I'm planning to try to come up with a pre-canned solution for this,
but in general you need to:
- Disable D3D11 support in the player settings and set D3D9 to use exclusive
  fullscreen. D3D11 will work with 3D, but having it enabled in Unity (even if
  not actually used) prevents exclusive full screen mode from being used, which
  in turn prevents 3D from engaging.
- Link against nvapi and use it to create a stereo texture to allow shaders to
  determine the current separation & convergence settings, and which eye is
  currently being drawn.
- Force all shadow maps to render in mono (how?).
- Apply the stereo correction formula to the output screen coordinates from the
  Internal-PrePassLighting vertex shader for everything except directional and
  screen lighting.
- Apply the view-space variation of the stereo correction formula to the output
  ray from the Internal-PrePassLightins vertex shader.
- subtract the view-space variation of the stereo correction formula in the
  Internal-PrePassLighting shader just before running the ray through the
  camera to world matrix.
- Subtract the view-space variation of the stereo correction formula in the
  Internal-PrePassCollectShadows shader just before running the ray through the
  camera to world matrix.
- Fix all surface shaders - I think this may be possible by simply fixing
  ComputeScreenPos() in UnityCG.cginc, but I have not confirmed this. This is
  also necessary even if only using forward lighting.
- If using a mouse cursor, render it in software - this is to allow it's depth
  to be customised.

The stereo correction formula is (note: eyesign is already included in the
separation obtained from the stereo params texture set up with nvapi):

    X += eyesign * separation * (depth - convergence)

The view-space variation of the stereo correction formula is (P.I is the
inverse projection matrix):

    X += eyesign * separation * (depth - convergence) * P.I[0,0]

or

    X += eyesign * separation * (depth - convergence) * tan(fov_horizontal / 2)
