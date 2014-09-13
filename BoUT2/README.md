The Book of Unwritten Tales 2
==============================

Fixed
-----
- Disables broken shadows (can be toggled on and off with U)
- Can adjust depth of in-game text and icons (item descriptions, subtitles,
  inventory, etc) by pressing keys on the number row. `~ will set screen depth,
  1-9 will set depth to 10%-90% and 0 sets depth to 100% separation.
- Halo on fog fixed

Known Issues
------------
- Adjusting separation with Ctrl+F3/F4 causes game to crash, so I recommend you
  have your desired separation set ahead of time.
- Adjusting convergence with Ctrl+F5/F6 causes further mouse clicks to be
  ignored, requiring the game to be restarted to make any meaningful progress.
  I suggest adjusting convergence while looking at the menu until the book just
  pops out of the screen, then restart the game and hopefully you won't need to
  adjust it further.
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
This is an early access episodic game and is likley to recieve numerous
updates which could break these fixes (update 2 already broke one). Be sure to
check the Helix blog for updates and if you find that one of my fixes no longer
works please let me know.

Interested in learning to fix 3D Games?
---------------------------------------
Come join us in bo3b's school for shaderhackers:
https://forums.geforce.com/default/topic/766890/3d-vision/bo3bs-school-for-shaderhackers

If you are interested in seeing what changes I made to fix this and other
games, I'd recommend checking out my 3d-fixes github repository - you can look
through the commit history to see exactly what I changed and why:

https://github.com/DarkStarSword/3d-fixes
