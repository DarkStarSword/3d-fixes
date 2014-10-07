Game Fixes
==========

Complete Fixes
--------------
- Betrayer (Improvements on Eqzitara's fix - fixes water, god rays, etc.)
- The Book of Unwritten Tales 2 (Early Access - expect updates)

Minor Improvements
------------------
- Far Cry 2 (Adds auto-convergence while holding RMB)
- Miasmata (Partial high quality water fix, no longer need Aion profile)

Work in Progress
----------------
- World of Diving (Partial shadow fix, fixed or disabled halos)

Misc
====
### useful_pre-commit_hook ###
If you are tracking 3D fixes in git, it is recommended to add this commit hook
to prevent accidentally committing a shader with a NULL byte so that git will
treat them as text files and show diffs in the history.

### float_to_hex.py ###
Small python scrip to convert floating point numbers to hex and vice versa to
get values for Helix Mod's DX9Settings.ini

### \__game_list__ ###
Source for the auto-updating game list on the Helix Mod blog.

### mkrelease.sh ###
Small script to package up a game's fixes for release, replacing the symlinked
dll with the real version and renaming README.md to 3DFix-README.txt. Run from
cygwin, Linux or another Unix environment.

### md2helix_blogger.py ###
Python script to format a markdown document to fit in with the formatting on
the Helix blog. Strips top level headers and downgrades second level headers to
underlined paragraphs.
