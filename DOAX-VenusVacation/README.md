Dead or Alive Xtreme Venus Vacation
===================================

This is not to be confused with the console exclusive game Dead or Alive Xtreme
3: Venus. This is a free to play casual volleyball *management* game, and lacks
the volleyball gameplay or minigames of its console counterpart.

There are two versions of this game - a Japanese version available through DMM,
and a recently released English version currently on Steam. The Japanese
version has been around for longer and has more content and features than the
English version, but obviously the English version is easier to understand and
is playing catch-up with old events from the Japanese version. Most mods will
work fine on either version (with some exceptions).

For help with installing the Japanese version refer to [this article][1] (the
camera mode of the Google Translate Android app may also be helpful for any
steps that have changed since this article was written), and [the beginners
guide][2] to understand the game itself and the [reddit][3] community for event
guides.

The English version is partially region locked and the store page is not
visible from most Western countries, however many people can trivially bypass
this by simply following [this link][4] to install the game. If that doesn't
work connect to a VPN endpoint in a South-East Asia country (e.g. Hong Kong or
Singapore, but NOT Japan) to install the game. Once installed you do not need
the VPN to play.

[1]: https://www.dualshockers.com/dead-alive-xtreme-venus-vacation-guide/
[2]: https://docs.google.com/spreadsheets/d/1rkWZB4DcKsKydZgpZzXrj7f1MGXRMJ3GDiqmEXeVQUw/edit#gid=1887486128
[3]: https://www.reddit.com/r/DOAXVenusVacation/
[4]: steam://install/958260

Costume Mods
------------
This mod primarily adds support for NVIDIA 3D Vision to the game, but it is
also required for the costume mods available for this game. If this is why you
are here you can ignore any of the information below that is specific to 3D
Vision users and just follow the instructions on the website that led you here.

This mod by itself will not change any costumes - for that you will need mod
packs available from elsewhere and extract them into the Mods directory. You
don't need to restart the game after installing a new mod - just press F10 in
game to load any new mods.

Some mod packs ship with optional parts of the mods that are not enabled by
default - look for any files or directories in the mod pack that is named
"DISABLED something", and remove the "DISABLED" from the filename to enable it.

Installing (3D Vision + Costume Mod users)
------------------------------------------
1. Extract the contents of the zip file to the game directory.

2. In the launcher (not the game), open settings (2nd button from the top) and
   change everything to the left-most option (lower quality options are known
   not to work).

3. **IMPORTANT (3D Vision Users only): Once the main game launches, press F7 to
   switch to exclusive full screen mode to engage 3D. Repeat this anytime you
   alt+tab out of the game to re-engage 3D.**

Keys (3D Vision + Costume Mod Users)
------------------------------------
- F1: Show help
- F2: Toggle costume mods
- Shift+F2: Cycle costume mod shadow modes (on/off/original)
- Mouse back button: Toggle HUD visibility
- Ctrl+F9: 3DMigoto performance monitor
- F10: Reload all mods
- Ctrl+Alt+F10: Reload all mods and reset to default configuration

Keys (3D Vision Users Only)
---------------------------
- F7: Full Screen
- ~: Toggle auto-convergence feature on and off
- Ctrl+F5: Reduce popout when auto-convergence is on
- Ctrl+F6: Increase popout when auto-convergence is on

Auto-Convergence (3D Vision Users Only)
---------------------------------------
This fix uses my new auto-convergence feature (first introduced in my Life is
Strange: Before the Storm fix) to automatically adjust the convergence while
playing to suit the various scenes and quick camera angles changes this game
does. For this game I have set it to try to keep everything inside the screen
(behind the HUD), while still maximising the 3D effect in any given scene.

The auto-convergence feature replaces the traditional meaning of 3D Vision's
convergence setting with a "popout" setting, which is similar to convergence,
but gives better results with a wider range of camera angles, monitor sizes and
viewing distances. The same keys that normally adjust the convergence will
adjust the popout instead when auto-convergence is enabled, and the popout
value will be displayed on screen while adjusting it.

This feature has a number of tunable parameters, which can be tweaked by
editing the [Constants] section in the ShaderFixes\auto_convergence.ini. These
tunables include things such as the initial popout, minimum and maximum
allowable convergence values, thresholds for how far the convergence is allowed
to get away from the target, and threshold for the anti-judder countermeasure.

3D Vision Fixes
---------------
- Lights & shadows
- Water
- HUD
- Added automatic convergence

3D Vision Update v1.1
---------------------
- Fixed ripples
- Fixed auto-convergence popout bias changing on full screen
- Use a lower convergence preset when Burst is activated

Update v1.2
-----------
- Fixed shadow glitch
- This fix now forms the basis for third party costume mods

Update v1.4
-----------
- Major 3DMigoto update (conditional logic, performance monitor)
- Auto-convergence performance cost will be skipped when 3D Vision is disabled
- Added toggle keys for costume mods and shadows (try cycling shadow modes if performance is an issue)
- New built in help shown by pressing F1
- Enabled costume mods for missing costume + shadow shaders
- Enabled costume and fingernail texture replacement mods
- Fix cases where a shadow could go missing from a costume mod
- HUD will always be shown in burst mode

Update v1.5
-----------
- Fix missing legs in some costume mods
- F2/Shift+F2 hotkeys now show status in overlay

Update v1.6
-----------
- Re-fixed lighting & auto-convergence broken by game update

Update v1.7
-----------
- Updated costume mod and 3D Vision ripple fix for compatibility with DOAXVV
  December 6th update
- Update to 3DMigoto 1.3.12 (adds vertex buffer hunting keys, clipboard marking
  mode, etc)
- 3D Vision: Made specular reflections on some (not all) materials render at
  their accurate depth instead of surface depth.
- 3D Vision: Tweaked auto-convergence settings for more comfort in some
  cutscenes.

Hotfix v1.8
-----------
- Fixed pink fingernails
- Added another missing costume shader

Update v1.9
-----------
- 3DMigoto updated to 1.3.14 to facilitate more advanced modding
- Now automatically saves the costume & shadow settings on exit/reload.
  Ctrl+Alt+F10 will revert to the default settings and reload.
- Key bindings are no longer processed while alt+tabbed out.
- Frame analysis now has several "profiles" that can be switched with - by
  default only skin and costumes are dumped to make blender imports faster.
  Press Ctrl+F8 (in hunting mode) to enable/disable dumping hair and
  fingernails, or switch to dumping UI textures instead.
- Frame analysis will no longer dump out modded meshes to make it a little
  easier to import meshes into blender when a costume mod is active (If you
  want to reimport a modified mesh you should be importing that directly from
  the mod, not a frame analysis dump).
- Auto-convergence has been updated - the popout bias will be automatically
  saved in the d3dx_user.ini, and the auto-convergence HUD will show the
  current convergence value as well. There's a bunch more changes under the
  hood, so it may behave slightly differently to before.

Update v2.0
-----------
- 3DMigoto updated to 1.3.15
- F10 reload is now much faster
- Settings left over from uninstalled mods will be removed on the next F10
  reload/game exit (You will still see these warnings once)
- Fix crash when news is displayed while using certain mods
- Displaying news will no longer reset certain settings
- Fixed compatibility issue with ReShade (if you couldn't use the two together
  before, please test again and report back)
- Fixed crash that could occur on non-nvidia systems in some circumstances

Update v2.1
-----------
- 3DMigoto updated to 1.3.16
- Fixed compatibility issue with new versions of ReShade
- Automatically adjust depth of icons in pool hopping minigame (3D Vision)

Update v2.2
-----------
- Updated costume mod for compatibility with DMM version 2019-04-25 update

Known Issues (3D Vision Users Only)
-----------------------------------
The news and Gacha probabilities windows and certain text boxes are blank while
in full screen (or when using ReShade). Alt+tab out of the game (not just
disabling 3D) and they will appear, and press F7 to re-enable 3D when done, but
of course if you are playing on DMM it is all in Japanese anyway. Visit
[reddit][5] for English translations and event guides.

[5]: https://www.reddit.com/r/DOAXVenusVacation/

Side-by-Side / Top-and-Bottom Output Modes (3D Vision Users Only)
-----------------------------------------------------------------
This fix is bundled with the SBS / TAB output mode support in 3DMigoto. To
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
[supporting me with a monthly donation on Patreon][6], and thanks again to
those that already do! While I prefer the more stable monthly support that
Patreon offers, I can of course understand that some of you prefer to make
one-off donations when you can, and for that you can use [my Paypal][7]. As a
reminder, these donations are to support me personally, and do not go to other
modders on this site.

[6]: https://www.patreon.com/DarkStarSword
[7]: https://www.paypal.me/DarkStarSword

_This mod is created with 3DMigoto (primarily written by myself, Bo3b and
Chiri), and uses Flugan's Assembler. See [here][8] for a full list of
contributors to 3DMigoto_

[8]: https://darkstarsword.net/3Dmigoto-stats/authors.html
