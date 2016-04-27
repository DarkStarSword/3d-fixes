Dreamfall Chapters (Books 1-4)
==============================

Update 2015-12-10
-----------------
This is a major update:

- Re-fixed game from scratch for the Unity 5 update

- Fixed Book 4

- Added an automatic depth adjustment to the HUD. The floating targeting icon
  and descriptive text will automatically adjust their depth to match whatever
  the icon is resting on. This is not 100% perfect (and the mouse cursor is
  still at screen depth), so it can be toggled on and off with Q.  
  [Info about the technique][1]

[1]: https://forums.geforce.com/default/topic/902840/3d-vision/i-fixed-unity-reflections-and-got-more-than-i-bargained-for/post/4754023/#4754023

- Brand new Unity lighting fix (yes, this is the second time this game has been
  used to develop a new lighting fix) - looks exactly the same as the old one,
  but it was necessary to work within some constraints in Helix Mod to also
  allow:

- Brand new Unity reflection fix. Aside from the obvious things like windows,
  glass, water, puddles, and even Zoe's eyes, this also adds a lot of small
  detail to many objects (literally thousands of shaders were adjusted to fully
  enable this). With Unity 5's physically accurate lighting model this makes
  the way light hits certain surfaces appear more realistic - hair has more
  detail, highlights reflecting on wooden surfaces are below the surface, and
  even things like Zoe's leather jacket reflect light in just the right way. I
  highly recommend loading a save from Book one and taking a stroll around
  Propast to see the difference this makes :)  
  [Screenshots and info about the technique][2]

[2]: https://forums.geforce.com/default/topic/902840/3d-vision/i-fixed-unity-reflections-and-got-more-than-i-bargained-for/

Installation
------------
1. Extract the contents of the zip file to the game directory.

2. If you are running the 32bit version of the game (the GOG version recently
   switched to 32bit, and Steam will install the 32bit version if your OS is
   32bit), replace the d3d9.dll with the one from the 32bit directory.

Fixed
-----
- Lighting and shadows

- Physically accurate reflections

- Glow around lights

- Halos on all surfaces

- Automatic HUD depth (toggle with Q)

- UI depth (except the mouse cursor and automatic HUD) is adjustable with the
  keys on the number row and tilde to return to screen depth.

Known Issues
------------
- Volumetric ray-marched light shafts are at screen depth and are disabled. You
  can re-enable them with U.

- The mouse cursor depth is not adjustable as it uses a hardware cursor.

- The Purple Mountains background is drawn closer than some of the foreground.
  This is not a skybox - it is in fact two scenes rendered on top of each other
  making it difficult to separate them.

Additional Notes
----------------
- I have not completely replayed the first three chapters since the Unity 5
  update. If you find something broken (especially things like glass or heat
  distortions), please let me know.

- I expect that I will need to update the fix as more books are released, so
  check back for updates.


Thanks to everyone who helped out on the forum to make the original Book 1 fix
possible, especially 4everAwake and mike_ar69! This was the game where we
cracked Unity 5 lighting and has enabled many more fixes since - shaderhackers
may be interested in reading through [this thread][3] for background on the
original technique.

[3]: https://forums.geforce.com/default/topic/781954/3d-vision/dreamfall-chapters

Like my Work?
-------------
Consider supporting me on [Patreon](https://www.patreon.com/DarkStarSword)
