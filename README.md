Stereoscopic 3D Fixes
=====================
This repository tracks any fixes I make to games rendered in stereoscopic 3D
using nVidia 3D Vision. Helix Mod and 3DMigoto are used to enable the fixes,
see the [Helix Mod blog][1] for details on  mod itself and final releases of
these fixes.

[1]: http://helixmod.blogspot.com.au/

### Complete Fixes ###
- [Betrayer](Betrayer) (Improvements on Eqzitara's fix) - fixes water, god rays, etc.
- [The Book of Unwritten Tales 2](BoUT2) - Fixes shadows, halos, etc.
- [Montague's Mount](Montague's Mount) - Fixes halos, shadows, etc.
- [Dreamfall Chapters](Dreamfall Chapters) - First ever Unity FOV correct shadow fix
- World of Diving [DX9](World of Diving (DX9)) & [DX11](World of Diving (DX11)) - Fixed halos, shadows, etc.
- [The Forest](The Forest) - Fixed halos, shadows, reflections, parallax sand/rocks, etc.
- [Legends of Aethereus](LegendsOfAethereus) - Fixed halos, shadows, skybox, etc.
- [DreadOut](DreadOut) - Fix for missing fog after shader model upgrade, stereo cameraphone, etc.
- [Eleusis](Eleusis) - Fixed shadows, light shafts, etc.
- [Stranded Deep](Stranded Deep) - Fixed water, light shafts, yet another shadow pattern, auto-crosshair, etc.
- [Life Is Strange](Life is Strange) - Fixed shadows, reflections, light shafts, bloom, etc.
- [Miasmata](Miasmata) - Reflections, light shafts, stereo crosshair, skybox, etc.
- [Oddworld: New 'n' Tasty](Oddworld New n Tasty) - Shadows, halos, clipping, ripple distortion, etc.
- [Pineview Drive](Pineview Drive) - Halos, shadows, sun shafts, etc.
- [The Long Dark](TheLongDark) - Halos, shadows, etc.
- [Viscera Cleanup Detail](Viscera) - shadows, missing UI, etc.
- [Dead or Alive 5: Last Round](Dead or Alive 5 Last Round) - water, halos, lens flares
- [The Last Tinker: City of Colors](The Last Tinker City of Colors) - new technique to fix shadows
- [Euro Truck Simulator 2](Euro Truck Simulator 2) - skybox, god rays, reflections
- [Lichdom Battlemage](Lichdom Battlemage) - first every CryEngine 3 fix
- [Mad Max](Mad Max) (Collaboration with DHR) - Fixes shadows, bloom, decals, reflections, etc.
- [Metal Gear Solid V: The Phantom Pain](MGSV_TPP) - New 3DMigoto hooking mode, accurate specular highlight fix, etc.
- [The Witness](The Witness) - Automatic stereo mouse cursor, reflections, etc.
- [Firewatch](Firewatch) - First game to use the DX11 port of my Unity scripts
- [Far Cry Primal](Far Cry Primal) - Volumetric fog / light shafts / shadow volumes, accurate specular highlights, etc.

Several of my fixes are in their own dedicated repository due to their size:
- [WATCH_DOGS2](https://github.com/DarkStarSword/3d-fixes-WATCH_DOGS2) - First ever accurate Screen Space Reflection fix, accurate San Francisco volumetric fog, etc.

Several of my fixes can be found in the 3DMigoto repository instead:
- [Far Cry 4](https://github.com/bo3b/3Dmigoto/tree/master/FC4) (with mike_ar69) - fixes pretty much everything, adds an auto HUD
- [Witcher 3](https://github.com/bo3b/3Dmigoto/tree/master/Witcher3) (with mike_ar69 & others) - Highlight: physical lighting compute shaders

### Works In Progress ###
- [Submerged](Submerged) (UE4 3DMigoto approach WIP, fixes shadows)
- [Batman: Arkham Knight](https://github.com/bo3b/3Dmigoto/tree/master/Batman) (with mike_ar69) - fixes tile lighting compute shaders and halos
- [Demonicon](demonicon) - Quick fix to make the game playable, fixes lights and some halos
- [Akiba's Trip](Akiba's Trip Undead & Undressed) - Adds a toggle for an auto UI depth adjustment (unpolished)

### Minor Improvements ###
- [Far Cry 2](Far Cry 2) - Adds auto-convergence while holding RMB
- [Infinifactory](Infinifactory) - fixes shadows from bo3b's fix

### Other Branches ###
There's a couple of fixes that aren't in the master branch for various reasons:
- [Crysis 3](https://github.com/DarkStarSword/3d-fixes/tree/crysis3/Crysis 3) - Assisting DHR with a few lights
- [Glare](https://github.com/DarkStarSword/3d-fixes/tree/glare/Glare) - Was unable to resolve clipping issue on lights at the time (I should revisit this - I believe I now know how to solve this)

### Templates ###
- [Unity 4](Unity)
- [Unity 5 DX9 Old view-space style fix](Unity5/DX9)
- [Unity 5 DX9 New world-space style fix](Unity5/DX9-New)
- [Unity 5 DX11 Hybrid style fix](Unity5/DX11)

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
pretty. At the moment it can (this list is out of date, run with --help for all
current features):
- Install shaders to the ShaderOverride directory, taking care of naming the
  file correctly.
- Convert ps_2_0 to ps_3_0 and vs_2_0 to vs_3_0, optionally adding instructions
  to preserve fog that can stop working on shader model upgrades.
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
- Attempt to automatically fix common issues in vertex shaders where the output
  position has been copied, often resulting in halos (Very helpful for Unity
  games).
- Automatically fix light shafts in Unreal Engine games.
- Remove Unreal's stereo correction in shaders using vPos where it does more
  harm than good.
- Automatically fix certain types of reflective surfaces in Unreal games (those
  using a 2D DNEReflectionTexture, used in Life Is Strange).
- Automatically fix shadows in Unreal Engine games.
- Apply auto fixes for Unity lights/shadows, specular highlights, reflections,
  fog, SSAO, etc (start with the [templates](Unity) instead).

### hlsltool.py ###
This is similar to shadertool.py, but works on HLSL shaders instead. It's
feature set is more limited than shadertool:
- Install shaders to the ShaderFixes directory.
- Attempt to automatically fix common issues in vertex shaders where the output
  position has been copied, often resulting in halos (Very helpful for Unity
  games).
- Apply auto fixes for Unity lights/shadows, specular highlights, reflections,
  fog, light shafts, etc (start with the [template](Unity/DX11) instead).

### asmtool.py ###
This is a port of shadertool.py to work with DX11 assembly shaders, (but
internally is more similar to hlsltool and depends on both for some common
code). It's feature set is the most limited for now:
- Install shaders to the ShaderFixes directory.
- Attempt to automatically fix common issues in vertex shaders where the output
  position has been copied, often resulting in halos (Very helpful for Unity
  games).
- Apply auto fixes for Unity lights/shadows, specular highlights, reflections,
  fog, light shafts, etc (start with the [template](Unity/DX11) instead).

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

### extract_unity53_shaders.py ###
Variant of the above for Unity 5.3 and later.

### extract_unreal_shaders.py ###
This script has been abandoned due to considerable complications in the Unreal
file formats. It can extract shader names from the Arkham Knight cooked shader
cache, but probably won't do anything useful in any other game. Consider using
the generic_shader_extractor.py script instead.

### generic_shader_extractor.py ###
This script can extract DX11 shaders from many games. It is known to work with
all UE4 games, but not Unity or CryEngine games, and may or may not work with
other games. It will not extract any additional metadata for the shaders other
than what 3DMigoto can already extract, but is useful for games that only dump
shaders on demand / level by level, or games that use GPU specific shaders.

### ddsinfo.py ###
Decodes the header on a DDS file and possibly converts it to PNG (conversion
only supported for some DDS formats, extending support as I come across new
formats, but I kind of want to rewrite the format support to be more
declarative).

For use with Helix Mod: Use GetSampler1FromReg, GetSampler2FromReg or
GetSampler3FromReg in a shader section of DX9Settings.ini to extract a texture
passed to a shader, press F12 in game to dump it out as Tex1.dds, Tex2.dds or
Tex3.dds, then use this tool to decode it's header.

For use with 3DMigoto: Use on .dds files dumped during frame analysis.

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

### unity_asset_extractor.py ###
An alternative to Unity Asset Explorer, to extract assets (currently limited to
shaders) from Unity 4 and Unity 5 games in batch.

### dx11shaderanalyse.py ###
Decodes some information in the ISGN & OSGN sections of DX11 shaders.

### pyasm.py ###
Implements shader like semantics in Python, including registers supporting
masks and swizzles using a natural syntax, and various shader instructions.
Useful to prototype & debug complicated algorithms.

### decode_buffer.py ###
Decodes the given buffer extracted via 3DMigoto's frame analysis feature as
both integers and floats.

### 3dvisionlive_download_button.user.js ###
User script to add a download button to images on 3D Vision Live.

### cleanup_unity_shaders.py ###
Removes shaders from a Unity game in this git repository that are no longer
found amongst the extracted shaders to stop a fix growing endlessly. Use only
for games that people should not be running old versions of (like early
access). Old shaders will still be in the git history if we need them.

### compare_shader_bins.py ###
This was a quick 'n' dirty means to repair the damage caused to a DX11 assembly
shader by the microsoft disassembler by comparing the original and otherwise
unmodified reassembled shader binaries to look for differences then patch
floating point values in the assembly text to compensate. In some cases this
may patch the wrong floating point value, but has worked remarkably well in
practice. This script is no longer required as 3DMigoto will now auto repair
assembly shaders when they are dumped.

### __profiles__ ###
A couple of scripts to help catalogue the driver profiles and normalise the
profile format to make it easier to compare changes between driver versions.

### shaderutil.py ###
Utility library used by shadertool and the shader database.

### find_frame_analysis_candidates.py ###
Provides statistics from a 3DMigoto frame analysis log.txt that may assist in
selecting a suitable shader to use as a trigger to start analysis at the more
interesting post-processing phase of the frame. Statistics include the
percentage of draw calls and dumped render targets would be saved, as well as
the total number of times each listed shader is used (not all shaders are
listed), and the number of simultaneous render targets used with each listed
shader (a series of consecutive shaders with a consistently high number of
render targets may indicate the long and uninteresting forward rendering phase
of the frame).

### photo-gallery ###
Scripts to statically convert .mpo and .jps files into different viewing
formats and create a website displaying them, with links to switch methods.

### 3dvisionlive.js ###
Javascript file to embed 3D photos from 3dvisionlive.com in a web page
providing links to switch between using the plugin, cross-eyed or distance
viewing methods, or anaglyph.

### inverse-cs.hlsl ###
Compute shader that can be injected with 3DMigoto to inverse arbitrary 4x4
matrices. Uses the parallel nature of the GPU to accelerate the inverse, and
3DMigoto can usually restrict this to run once per frame to minimise the
performance impact. Extremely useful for inversing matrices to be passed to
assembly shaders, where performing an inline inverse is complicated and error
prone.

### rename2bytecode.sh ###
Script to rename shaders to use the bytecode hash. Requires a ShaderCache
folder containing all replaced shaders dumped with their current hashes in
binary form.

### rename2embedded.sh ###
As above, but renames the shaders to use the embedded hash.

### update_3dmigoto_symlinks.sh ###
Updates all 3DMigoto symlinks in the current directory or subdirectories to use
the latest version of 3DMigoto (which must be extracted in a directory named
3Dmigoto-x.y.z under 3d-fixes).

### custom_shader_cb_live_view ###
This directory contains a custom shader, font and the corresponding d3dx.ini
sections to interpret a constant buffer as floating point values and show them
live while in game. This is done entirely on the GPU and uses a geometry shader
to generate the text.
