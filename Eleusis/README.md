Eleusis
=======

Fixed
-----

- Moonlight shafts and glow around moon
- Dynamic Shadows
- Clipping on lights
- Water & glass refraction
- UI depth adjustable with 1-9 on number row, tilde for screen depth, 0 for
  99.5% depth. 9 (90%) is the default.
- The default point crosshair has been disabled (the hand icon will still
  show). Press Q to toggle this on and off (turning it on is useful to target
  small items, or trying to pick up a rock while running).

Installation
------------
Extract zip file under:

    ...\Eleusis\Binaries\Win32

Recommended: Disable Ambient Occlusion in the game settings. This is broken
even in 2D in this game as it uses outdated depth information. Note that
changing this or any other setting will break the fix, press Ctrl+T twice or
restart the game to restore it.

Known Issues
------------

- After changing any settings in the game the fix will break. Press Ctrl+T
  twice or restart the game to fix it.

- Sometimes after alt+tabbing out of the game the depth adjustment for the hand
  cursor stops working until the game is restarted.

- Some of the text in the credits has 2x depth adjustment applied for some
  reason. Set the UI depth to 50% or lower with the number row during the
  credits to avoid text beyond infinity.

Like my Work?
-------------
Consider supporting me on [Patreon](https://www.patreon.com/DarkStarSword)
