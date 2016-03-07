Far Cry Primal
==============

Fixed
-----
- Halos
- Lights / Shadows
	- Tile Lighting
	- Directional
	- Ambient
	- Physical
- Volumetric fog
	- Shadow volumes (e.g. cast from trees)
	- Light volumes (e.g. in caves)
	- Camp fires
	- Density near mountains
- Specular highlights (Accurate!)
- Lens flares
- Auto crosshair added
- Water reflections
	- Real reflections outdoors (using stereo reversal technique)
	- Environment map reflections in caves
- Ambient Occlusion
	- Normal map artefacts
	- Disabled velocity smearing
- Vignette
- Hunter vision yellow outline fade out
- Underwater caustics

Installation
------------
1. Assign the game to the Far Cry 4 profile
2. Unpack the zip file to the Far Cry Primal\bin directory

Convergence Presets
-------------------
Press backslash to cycle between two convergence presets - a low preset
recommended for most of the game, and a high preset for use with the owl &
mammoth.

The high preset may also be activated by holding the Z key for 1.4 seconds
while calling the owl. Tapping Z will return to the recommended convergence.

You may customise these values by editing the d3dx.ini under
\[KeyConvergenceCycle\], \[KeyOwlConvergence\] and \[KeyOwlConvergenceLeave\].

Notes
-----
The auto HUD adjustment is applied to the entire HUD as a temporary measure
until I have improved the performance of tracking texture hash updates.

Like my Work?
-------------
Consider supporting me on [Patreon](https://www.patreon.com/DarkStarSword)

_Special thanks to Flugan for his work on the assembler, used in this fix_
