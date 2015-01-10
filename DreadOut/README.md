DreadOut
========

Fixed
-----
- Halos fixed on all surfaces
- Shadows fixed
- Image on camera is now 3D (necessary to avoid rendering artefacts, hold Q
  with camera out if you prefer 2D).
- Convergence preset provided in-game to place the camera at a usable depth
- Automatic convergence preset used in menus to bring them close to screen
  depth (the main menu takes a moment to adjust after starting the game).
- Slight depth adjustment to the book in the pause menu

Known Issues
------------
If you find the image on the phone camera looks wrong (2D, doubled or tripled
image, flickering or broken shadows), alt+tab out of the game and back in. This
happens inconsistently - sometimes the image will look fine, then it will be
broken the next time you pull out the camera, so it's a good idea to check the
camera half a dozen times or so while you are in a safe area before moving on.

The rendering seems to be stable after a single alt+tab, so you might just want
to do one after launching the game for good measure.

If you are in a tight spot and don't have time to alt+tab, holding Q will
temporarily set the separation to 1% which will make the image on the camera
usable.

Installation (64bit)
--------------------
1. Extract the zip file to the game directory

Installation (32bit)
--------------------
1. Extract the zip file to the game directory
2. Replace the d3d9.dll with the one in the 32bit directory
