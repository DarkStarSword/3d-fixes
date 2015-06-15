The Book of Unwritten Tales 2
=============================

The fix has been updated for the final release with all five chapters. Special
thanks to KING Art for granting me access to the Chapter 5 private beta to get
this fix ready ahead of time :)

Shadows are now fixed. If you have installed a previous version of this fix, be
sure to delete the ShaderOverride folder before installing the new version,
otherwise shadows will still be disabled.

Fixed
-----
- Shadows, halos, etc.
- Manual convergence and UI depth presets added (see below)
- Menus, books and maps automatically activate custom separation, convergence
  and UI depth presets tailored to each one.

Keys
----
I recommend you get comfortable with switching between different convergence
and UI depth presets to suit each individual scene in the game. The recommended
L preset is conservative to make it usable for the entire game (except for the
drunken punch minigame in chapter 2, which needs the K preset), but some scenes
may look better with a higher convergence.

UI, subtitles and inventory depth adjustment (not mouse cursor):

- ~: Screen depth
- 1-9: 10-90% depth
- 0: 100% depth

Convergence presets:

- K: Low convergence preset for the drunken punch minigame in chapter 2
- **L: Recommended preset for most of the game**
- semicolon: High preset for extra pop (can be too high in some scenes)
- quote: Extra high preset for extreme pop (can be too high in some scenes)

The convergence presets on K and L are fixed, but the presets on semicolon and
quote can be customised to your preference. Start by activating the preset,
adjusting the convergence with Ctrl+F5/F6 (advanced key bindings must be
enabled in the control panel), then press F7 to save.

Known Issues
------------
- Mouse cursor depth cannot be adjusted as the game uses a hardware cursor.
- The default convergence preset does not get activated automatically when the
  game is launched. Press L to manually activate it after launching the game.
- There's a few scenes in the game where the background is little more than a
  pre-rendered texture drawn over extremely simplified 3D geometry that doesn't
  really look very convincing in 3D. Fortunately there are only a few of these
  (mostly when talking to other characters, and mostly in chapter 1) and
  outside of them the 3D looks fantastic!

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

**After launching the game, press L to activate the recommended convergence
preset.**

Notes
-----
- I have not found all the optional side quests in the game yet. If you notice
  a rendering issue in one of them, or find more books that need a custom
  stereo preset please let me know.
- I updated the fix during the chapter 5 private beta, but have not thouroughly
  checked if anything changed for the public release. Let me know if you find
  something broken.

Interested in learning to fix 3D Games?
---------------------------------------
Come join us in [bo3b's school for shaderhackers][1]!

If you are interested in seeing what changes I made to fix this and other
games, I'd recommend checking out my [3d-fixes github repository][2] - you can
look through the commit history to see exactly what I changed and why.

[1]: https://forums.geforce.com/default/topic/766890/3d-vision/bo3bs-school-for-shaderhackers
[2]: https://github.com/DarkStarSword/3d-fixes
