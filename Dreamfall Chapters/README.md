Dreamfall Chapters
==================

Installation
------------
Extract the contents of the zip file to the game directory.

If the graphics are broken after launching the game or after alt+tabbing out
and in, try adjusting the separation settings with Ctrl+F3/F4. You may need to
hold the lower separation button for about a second to fix it, then you can
adjust it back to your preferred settings.

Fixed
-----
- Lighting and shadows fixed with a new technique
- Halos on all surfaces, reflections, etc.
- UI depth (except the mouse cursor) is adjustable with the keys on the number
  row and tilde to return to screen depth.

Known Issues
------------
- Volumetric ray-marched light shafts are disabled. You can re-enable them with
  U and toggle them between no fix (at screen depth), and a partial inaccurate
  fix that causes a halo around the character and other objects inside them.
- Reflections are mono
- The mouse cursor depth is not adjustable as it uses a hardware cursor.

Additional Notes
----------------
- I played the game on the awesome quality setting. If you are playing on a
  lower setting and notice any broken surfaces, please let me where in the game
  you saw it and what settings you were using.
- I expect that I will need to update the fix as more books are released, so
  check back for updates.
- The game runs in a borderless full-screen window. It should automatically
  select a profile which will work in this mode, but if the 3D doesn't engage
  when running the game use nVidia inspector to remove it from any profile it
  has been assigned to.


Thanks to everyone who helped out on the forum to make this fix possible,
especially 4everAwake and mike_ar69! Together we have pioneered new techniques
for fixing broken lighting and shadows in Unity games, so this thread may be of
interest to other shaderhackers:

<https://forums.geforce.com/default/topic/781954/3d-vision/dreamfall-chapters>
