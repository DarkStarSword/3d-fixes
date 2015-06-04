Unity 5 Viking Village 3D Vision Demo
=====================================

This is a demonstration of using 3Dmigoto to fix a DX11 Unity 5 game. Note that
for it to work, the game must use exclusive-mode full screen rather than a
full-screen window. This demo does that, but it should be noted that alt+tab
handling is broken in Unity in this configuration, so most games are likely to
opt to use a full-screen window instead (and this is the default in Unity).

DX9 games can always use a profile to enable 3D in windowed mode (though this
has some limitations, such as not being able to set the surface creation mode),
but we may need to force DX11 games to use exclusive-mode to allow them to work
with 3D.

Fixed
-----
- Directional shadows
- Point lights/shadows
- "Physical lighting" (global illumination, specular highlights, environment reflections)
- Water halo/reflection
- Smoke halo
- Fire halo
- Sun flare
- Highlights on Depth of Field blur (around torches during demo fly-by mode)

Keys
----
- Press backslash to set the recommended convergence preset
- Hold F9 to show what the village looked like without the fix
- Press C to show the demo fly-by mode
- Press space to jump
- Double tap space to start flying

Directional Shadows
-------------------
These are easier to fix in Unity 5 than they were in Unity 4, as the vertex
shader now has direct access to the inverse projection matrix, which is added
as an extra output to pass to the pixel shaders where it can be used to apply
the view-space stereo correction to fix the shadows.

Point Lights & Shadows
----------------------
These follow much the same pattern as Unity 4. They do not have direct access
to the inverse projection matrix, but it can be derived from the model-view and
model-view-projection matrices that it does have access to. This fix performs
the (partial) model-view matrix inversion inside the vertex shader and passes
the result to the pixel shaders to fix the shadows.

Note that the vertex shader tests W to determine if it is being used to draw an
in-world point or spot light, otherwise it is drawing a full-screen effect,
such as...

Physical Lighting
-----------------
This uses the same vertex shader as point & spot lights. However, it is
performed on the full screen and as such the model-view and
model-view-projection matrices are not usable to determine the
inverse-projection matrix. Currently this case uses a hard-coded FOV value to
perform the correction - in the future support will be added to 3Dmigoto to
copy the necessary matrices or constant buffers in to this shader so that the
fix will be independent of the FOV.

Water halo/reflection, Smoke Halo & Fire Halo
---------------------------------------------
These all follow much the same pattern - the output position from the vertex
shader has been used for other purposes (e.g. depth buffer sampling, reflection
position) so a stereo correction is added to make these use the adjusted stereo
position.

A nice change from Unity 4 is that this is no longer necessary to fix on every
surface shader - it is now restricted to the usual suspects (mostly
semi-transparent effects).

Sun flare
---------
This shader already had a reasonable depth value, but it is drawn with the
depth buffer disabled and was confusing the driver's heuristics causing it to
jump between screen depth and near infinity.

We apply the standard stereo correction, then scale the output coordinate to
make W == convergence, which prevents the driver's stereo correction from
moving it further, regardless of what it's heuristics decide.

Note that we do not apply the stereo correction if W == 1, as that usually
signifies that the shader is drawing a UI element. We also do not scale the
coordinate if convergence == 0, as that would disable the effect when stereo is
disabled.

Depth of Field Blur
-------------------
This shader had two passes of interest - in the first pass the shader creates a
list of pixels that are brighter than a certain threshold and appends them to a
structured buffer, and in the second pass it renders a highlight around these
pixels. Unlike textures, structured buffers cannot be stereoised, so this
two-stage approach effectively lost the eye information of each point causing
the highlights to appear in three positions.

The fix encodes information about which eye the point came from into the
structured buffer (by negating one field for the right eye), and the second
shader is then able to use this extra data to discard points meant for the
other eye.
