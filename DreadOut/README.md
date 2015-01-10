DreadOut
========

Fixed
-----
- Shadows fixed
- Halos fixed on all surfaces (slight variation of the usual technique to allow
  fog to continue to work on affected shaders)
- Image on camera-phone is now 3D (necessary to avoid rendering artefacts)
- Convergence preset provided in-game to place the camera at a usable depth
- Slight depth adjustment to the book in the pause menu to line up with the UI

Known Issues
------------
- Mouse cursor depth cannot be adjusted as the game uses a hardware cursor.
  Hold Q to reduce 3D in the menus to allow for easier selection.

- If you find the image on the phone camera looks wrong (2D, doubled or tripled
  image, flickering, black areas or broken shadows), put the camera away and
  open it again.  If you find that this is happening a lot try alt+tabbing out
  of the game and back in, or quit and restart the game. If you are in a tight
  spot and don't have time to put the camera away, holding Q will temporarily
  set the separation to 1% which will make the image on the camera mostly
  usable.

Installation (64bit)
--------------------
1. Extract the zip file to the game directory

Installation (32bit)
--------------------
1. Extract the zip file to the game directory
2. Replace the d3d9.dll with the one in the 32bit directory

Notes
-----
I played the game on the highest available quality setting ("Fantastic") at
1920x1080. If you see any rendering issues or the camera is in 2D, switch to
these settings (I don't know if there are any issues on other settings - I
haven't checked).
