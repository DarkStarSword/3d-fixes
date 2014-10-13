Stereoscopic 3D Fixes
=====================
This repository tracks any fixes I make to games rendered in stereoscopic 3D
using nVidia 3D Vision. Helix Mod and 3DMigoto are used to enable the fixes,
see the [Helix Mod blog][1] for details on  mod itself and final releases of
these fixes.

[1]: http://helixmod.blogspot.com.au/

### Complete Fixes ###
- Betrayer (Improvements on Eqzitara's fix - fixes water, god rays, etc.)
- The Book of Unwritten Tales 2 (Early Access - expect updates)

### Minor Improvements ###
- Far Cry 2 (Adds auto-convergence while holding RMB)
- Miasmata (Partial high quality water fix, no longer need Aion profile)

### Work in Progress ###
- World of Diving (Partial shadow fix, fixed or disabled halos)

Misc
====
I also keep a small collection of utilities related to 3D fixes.

### useful_pre-commit_hook ###
If you are tracking 3D fixes in git, it is recommended to add this commit hook
to prevent accidentally committing a shader with a NULL byte so that git will
treat them as text files and show diffs in the history.

### float_to_hex.py ###
Small python script to convert floating point numbers to hex and vice versa to
get values for Helix Mod's DX9Settings.ini

### \__game_list__ ###
Source for the auto-updating game list on the Helix Mod blog.

### \__shader_database__ ###
Python script to crawl the helix blog downloading every fix it can find and
creating a database of shaders so we can look up if a particular shader has
been fixed previously, as may happen with games using the same engine.

### mkrelease.sh ###
Small script to package up a game's fixes for release, replacing the symlinked
dll with the real version and renaming README.md to 3DFix-README.txt. Run from
cygwin, Linux or another Unix environment.

### md2helix_blogger.py ###
Python script to format a markdown document to fit in with the formatting on
the Helix blog. Strips top level headers and downgrades second level headers to
underlined paragraphs.

### CustomSettingNames_en-EN.xml ###
Custom setting names XML file for nVidia Inspector that adds friendly names for
some of the stereo attributes that I've identified in each profile.

### shadertool.py ###
This is a python tool I've started working on to parse shaders and automate
some of the process of hacking them. It's very early and the code is not very
pretty. At the moment it can:
- Install shaders to the ShaderOverride directory
- Convert ps_2_0 to ps_3_0 and vs_2_0 to vs_3_0
- Analyse shader register usage and look for free constants.
