Dreamfall Chapters (Books 1-4 Work In Progress)
===============================================

Update 2015-12-05
-----------------
This is an early release to make the Unity 5 and Book 4 updates playable.
There are some known rendering issues that I have not re-fixed yet, and I have
not completed Book 4 to fix further issues, so I would recommend waiting a few
days for a more polished fix.

Installation
------------
1. Extract the contents of the zip file to the game directory.

2. If you are running a 32bit OS, replace the d3d9.dll with the one from the
   32bit directory.

Fixed
-----
- Lighting and shadows
- Halos on all surfaces, reflections, etc.
- UI depth (except the mouse cursor) is adjustable with the keys on the number
  row and tilde to return to screen depth.

Known Issues
------------
- Volumetric ray-marched light shafts are at screen depth and are disabled. You
  can re-enable them with U.
- Reflections are mono
- The mouse cursor depth is not adjustable as it uses a hardware cursor.

Additional Notes
----------------
- I played the game on the awesome quality setting. If you are playing on a
  lower setting and notice any broken surfaces, please let me where in the game
  you saw it and what settings you were using.
- I expect that I will need to update the fix as more books are released, so
  check back for updates.


Thanks to everyone who helped out on the forum to make this fix possible,
especially 4everAwake and mike_ar69! Together we have pioneered new techniques
for fixing broken lighting and shadows in Unity games, so this thread may be of
interest to other shaderhackers:

<https://forums.geforce.com/default/topic/781954/3d-vision/dreamfall-chapters>
