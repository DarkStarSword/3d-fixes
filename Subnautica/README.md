Subnautica
==========

This release officially brings support for Unity 5.6 to my template (shader
extraction support is also added for Unity 2017.1, 2017.2 & 2017.3 formats) :)

Update v1.1
-----------
- Adjusted several more HUD elements (resource blips, battery swap icons)
- Fixed various interior water surfaces (e.g. Moon Pool)
- Fixed Seamoth & Cyclops sonar ping
- Low convergence toggle key added (useful for the Seaglide's terrain hologram)
- Auto HUD adjustment now rests on in-world HUD elements (e.g. Cyclops Cockpit)
- Crosshair re-enabled by default to make in-world HUD elements easier to use
  (press X to disable as before)

Fixed
-----
- Halos
- Lights & shadows
- Screen Space Reflections (two types)
- Underwater light rays
- Water refraction (look at the moon viewed from below the surface)
- Automatically adjust HUD & crosshair depth
- Fix flickering HUD
- Disabled crosshair (X to toggle)
- Automatic convergence & mouse depth preset when PDA is active
- Adjusted scuba mask depth to be just slightly behind the screen, but still 3D
  (see x1 in the d3dx.ini to change the depth, or use the game's built in F6
  hotkey to cycle between several options, some of which disable the scuba mask)

Installation
------------
1. Extract the contents of the zip file to the game directory.

2. If you are running the 32bit version of the game, replace the DLLS with the
   ones in the 32bit directory.

3. Right click on the game in Steam and go to "Properties" -> "Set Launch
   Options" and enter "-window-mode exclusive" (without the quotes) and click
   "Ok"

4. Disable motion blur in the game settings.

5. Set Anti-Aliasing=FXAA

Keys
----
X: Toggle crosshair visibility

Caps Lock: Toggle low convergence preset to keep the hands behind the mask and
           make the Seaglide's terrain hologram easier to see.

\: Set high convergence preset recommended for a stronger 3D effect.

F6: Cycle various HUD & self display options (game shortcut, not mine. Beware
    that this conflicts with the convergence hotkeys, and you may have to press
    it several times to make everything visible again).

Known Issues
------------
- The horizon is not quite right when the camera is tilted.
- Certain fog effects are not quite even between both eyes.
- Performing a self-scan underwater briefly reveals the original depth of the
  scuba mask.
- The mouse cursor does not line up with the vehicle modification station when
  customising a vehicle's colour (no apparent way to distinguish between this
  scenario and the main menu).

Side-by-Side / Top-and-Bottom Output Modes
------------------------------------------
This fix is bundled with the new SBS / TAB output mode support in 3DMigoto. To
enable it, edit the d3dx.ini, find the [Present] section and uncomment (remove
the semicolon) the line that reads:

    run = CustomShader3DVision2SBS

Then, in game press F11 to cycle output modes. If using 3D TV Play, set the
nvidia control panel to output checkerboard to remove the 720p limitation.

Like my Work?
-------------
Fixing games takes a lot of time and effort, and I also do a lot of work on
3DMigoto behind the scenes to make all of these mods possible.

If you are in a position where you are able to do so, please consider
[supporting me with a monthly donation on Patreon][1], and thanks again to
those that already do! While I prefer the more stable monthly support that
Patreon offers, I can of course understand that some of you prefer to make
one-off donations when you can, and for that you can use [my Paypal][2]. As a
reminder, these donations are to support me personally, and do not go to other
modders on this site.

[1]: https://www.patreon.com/DarkStarSword
[2]: https://www.paypal.me/DarkStarSword

_This mod is created with 3DMigoto (primarily written by myself, Bo3b and
Chiri), and uses Flugan's Assembler. See [here][3] for a full list of
contributors to 3DMigoto_

[3]: https://darkstarsword.net/3Dmigoto-stats/authors.html

_Very special thanks to Neovad for a [previous version][4] of this fix while
the game was still in early access, and all his work applying my Unity
techniques to so many games I am not able to look at personally :)_

[4]: http://helixmod.blogspot.com/2017/06/subnautica-dx11.html
