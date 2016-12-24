ABZU
====

Fixed
-----
- Killed motion blur (causes massive issues in 3D)
- Fixed Temporal Anti-Aliasing (the game inexplicably enables this about half
  way though)
- Halos and related issues on all surfaces (grass, rocks, water, etc, etc, etc)
- Decals
- Lights
- Shadows
- Specular Highlights
- Environmental reflections
- Sun reflection
- Water clipping near walls
- Water caustics
- Water density

Installation
------------
1. Extract the zip file to the game directory. If done correctly, the d3d11.dll
   should be in the same directory as AbzuGame-Win64-Shipping.exe (not the top
   level directory)

2. Launch the game. The first time you run it (and again after any driver
   update) you will get a UAC prompt for Rundll32 to install the driver
   profile - choose yes.

SLI Notes
---------
SLI + 3D Vision is broken in this game in recent drivers. The surface of the
water is badly visually corrupted and the waves on the surface do not match
between the eyes. Either disable SLI through the control panel, or downgrade to
a known working driver:

- 372.90 (Wed Sep 21, 2016): Works
- 373.06 (Thu Oct 06, 2016): Works
- 375.63 (Sun Oct 23, 2016): Broken
- 375.70 (Fri Oct 28, 2016): Untested, presumed broken
- 375.95 (Fri Nov 18, 2016): Broken
- 376.09 (Mon Nov 28, 2016): Broken
- 376.19 (Mon Dec 05, 2016): Untested, presumed broken
- 376.33 (Wed Dec 14, 2016): Broken
- 376.48 (Wed Dec 21, 2016): Broken

Known Issues
------------
- If you see a massively broken effect (like a flickering surface, nuclear
  lights, an inexplicable colour filter, etc) it might just be a glitch. Try
  restarting the game before reporting any issues.

- About half way through the game it suddenly enables temporal anti-aliasing
  for no apparent reason, which has issues in 3D. I've fixed all the worst
  problems this causes, but it still exhibits some minor judder in some areas.

Side-by-Side / Top-and-Bottom Output Modes
------------------------------------------
This fix is bundled with the new SBS / TAB output mode support in 3DMigoto. To
enable it, edit the d3dx.ini, find the [Present] section and uncomment the line
that reads:

    run = CustomShader3DVision2SBS

Then, in game press F11 to cycle output modes. If using 3D TV Play, set the
nvidia control panel to output checkerboard to remove the 720p limitation.

Like my Work?
-------------
Modding games takes a lot of time and effort, not to mention the work I do
behind the scenes improving our tools and helping others. If you like what I
do, consider supporting me on [Patreon](https://www.patreon.com/DarkStarSword)
for a recurring donation or [Paypal](https://www.paypal.me/DarkStarSword) for a
one off.
