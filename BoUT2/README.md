The Book of Unwritten Tales 2 (Chapters 1 & 2)
==============================================

Fixed
-----
- Disables broken shadows (automatically re-enabled when switching to 2D). Some
  shadows work in 3D and these have been left enabled.
- Can adjust depth of in-game text and icons (item descriptions, subtitles,
  inventory, etc) by pressing keys on the number row. `~ will set screen depth,
  1-9 will set depth to 10%-90% and 0 sets depth to 100% separation.
- Halo on fog fixed
- Halo on magnifying glass' light beam fixed
- Two convergence presets are provided: L sets a reasonable convergence for
  most of the game and K sets a lower convergence suitable for the drunken
  punch minigame in chapter 2. Convergence can still be adjusted manually, but
  beware the issue with the F6 key mentioned below.

Known Issues
------------
- Adjusting separation with Ctrl+F3/F4 causes game to crash, so I recommend you
  have your desired separation set ahead of time.
- Pressing F6 will cause the game to stop responding to further mouse clicks,
  which makes adjusting convergence with the default keybindings challenging.
  You can use the L and K keys to select different convergence presets, or be
  prepared to restart the game after manually adjusting the convergence.
- Mouse cursor depth cannot be adjusted as the game uses a hardware cursor.
- The reflections in the mirror in Ivo's bedroom are broken.
- There's a few scenes in the game where the background is little more than a
  pre-rendered texture drawn over extremely simplified 3D geometry that doesn't
  really look very convincing in 3D. Fortunately there are only a few of these
  (mostly when talking to other characters) and outside of them the 3D looks
  fantastic!

Installation
------------
Extract the contents of 3Dfix-BoUT2.zip to the game directory. You should end
up with this directory structure:

    ...\The Book of Unwritten Tales 2\Windows\BouT2_Data\
    ...\The Book of Unwritten Tales 2\Windows\BouT2.exe
    ...\The Book of Unwritten Tales 2\Windows\steam_api.dll
    ...\The Book of Unwritten Tales 2\Windows\d3d9.dll	(new)
    ...\The Book of Unwritten Tales 2\Data\
    ...\The Book of Unwritten Tales 2\ShaderOverride\	(new)
    ...\The Book of Unwritten Tales 2\DX9Settings.ini	(new)

Notes
-----
This is an early access episodic game and is likely to receive numerous
updates which could break these fixes (update 2 already broke one). Be sure to
check the Helix blog for updates and if you find that one of my fixes no longer
works please let me know.

Interested in learning to fix 3D Games?
---------------------------------------
Come join us in [bo3b's school for shaderhackers][1]!

If you are interested in seeing what changes I made to fix this and other
games, I'd recommend checking out my [3d-fixes github repository][2] - you can
look through the commit history to see exactly what I changed and why.

[1]: https://forums.geforce.com/default/topic/766890/3d-vision/bo3bs-school-for-shaderhackers
[2]: https://github.com/DarkStarSword/3d-fixes
