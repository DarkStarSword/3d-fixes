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
- Montague's Mount (Fixes halos, shadows, etc.)
- Dreamfall Chapters Book 1 (First ever Unity FOV correct shadow fix)
- World of Diving (Fixed halos, shadows, etc.)
- The Forest (Fixed halos, shadows)

### Minor Improvements ###
- Far Cry 2 (Adds auto-convergence while holding RMB)
- Miasmata (Partial high quality water fix, no longer need Aion profile)

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
- Install shaders to the ShaderOverride directory, taking care of naming the
  file correctly.
- Convert ps_2_0 to ps_3_0 and vs_2_0 to vs_3_0
- Analyse shader register usage and look for free constants.
- Disable an entire shader by setting it's output to 0 or 1.
- Disable individual texcoord outputs from a vertex shader.
- Apply the stereo correction formula to an output texcoord of a vertex shader,
  optionally with a custom multiplier (try 0.5 if a correction switches eyes).
- Reverse the stereo correction formula on the output position of a vertex
  shader to unstereoize it.
- Disabled outputs, adjustments, etc. can be made conditional on a register
  passed in from Helix mod.
- Insert a depth adjustment suitable for UI elements to the value of a constant
  register component (typically passed in from DX9Settings.ini).

### extract_stereo_settings.py ###
Short python script to extract the table of Stereo settings from the nVidia
driver and write them to a CustomSettingNames_en-EN.xml which can be used with
nVidia Inspector.

### matrix.py ###
Small Python module to create typical matrices for translation, rotation,
scaling and projection in 3D to help me understand the maths behind them.

### extract_unity_shaders.py ###
Python script to parse the compiled output of Unity shaders and pull out all
the different variants into separate files, with headers intact.

### ddsinfo.py ###
Decodes the header on a DDS file. Use GetSampler1FromReg, GetSampler2FromReg or
GetSampler3FromReg in a shader section of DX9Settings.ini to extract a texture
passed to a shader, press F12 in game to dump it out as Tex1.dds, Tex2.dds or
Tex3.dds, then use this tool to decode it's header. This doesn't (yet) convert
it into another image format (but doing so would not be hard to add - I already
have a version that can decompress S3 textures in my Miasmata-fixes
repository, or you can always look for other tools to decode or show DDS files).

The idea here is to narrow down the list of render targets in the LOG.txt when
searching for a surface that needs to be stereoised - e.g. you can match the
FourCC with a Format and the Width & Height (Possibly Levels - is that mip-maps
by any chance?).

### interlaced2jps.py ###
Converts an interlaced image into a jps file

### screenshot_archive.py ###
This script periodically sorts all 3D screenshots into directories for the
games they are from and renames them to include the date and time they were
taken.

Place it in the Documents\NVStereoscopic3D.IMG directory and run it.

### \__shaderasm__ & shaderasm.exe ###
Small C++ project to assemble a shader .txt file. Used by
extract_unity_shaders.py to calculate the CRC32 of shaders extracted from Unity
games.

### calc_shader_crc.py ###
Small wrapper around shaderasm.exe to calculate a shader's current CRC32.
