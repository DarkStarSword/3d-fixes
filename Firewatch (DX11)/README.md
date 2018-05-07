Firewatch (DX11)
================

Update 2018-04-26
-----------------
The fix has been entirely redone from scratch for the Unity 5.6 update of this
game. **Note that the installation instructions have changed, and you now need
to edit the launch options to enable full screen mode**

Update 2016-11-07
-----------------
The fix has been entirely redone from scratch for the Unity 5.4 update of this
game. **Be sure to use the uninstall.bat to remove the old version of the fix
before installing this one.**

- The UI will now automatically return to screen depth whenever the mouse
  cursor is visible to make menu navigation easier.

- Fog (and certain related shadows) are now accurately fixed.

Fixed
-----
- Lights
- Shadows
- Specular highlights
- Glow around lights
- Light shafts
- Automatically adjust crosshair depth
- Fog

Installation
------------
1. Extract the zip file to the game directory

2. If you are on a 32bit OS, replace the DLLs with those in the 32bit
   directory.

3. Right click on the game in Steam and go to "Properties" -> "Set Launch
   Options" and enter "-window-mode exclusive" (without the quotes) and click
   "Ok"

4. Disable motion blur, as it causes some rendering artefacts.

Keys
----
- x: Toggle crosshair on and off

- Backslash: Activate recommended convergence preset

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
Fixing games takes a lot of time and effort, and I am currently otherwise
unemployed largely due to my ongoing [battle with mental health issues][1].

If you are in a position where you are able to do so, please consider
[supporting me with a monthly donation on Patreon][2], and thanks again to
those that already do! While I prefer the more stable monthly support that
Patreon offers, I can of course understand that some of you prefer to make
one-off donations when you can, and for that you can use [my Paypal][3]. As a
reminder, these donations are to support me personally, and do not go to other
modders on this site.

[1]: https://forums.geforce.com/default/topic/1000942/3d-vision/where-has-darkstarsword-been-/
[2]: https://www.patreon.com/DarkStarSword
[3]: https://www.paypal.me/DarkStarSword

_This mod is created with 3DMigoto (primarily written by myself, Bo3b and
Chiri), and uses Flugan's Assembler. See [here][4] for a full list of
contributors to 3DMigoto_

[4]: https://darkstarsword.net/3Dmigoto-stats/authors.html
