Dead or Alive Xtreme Venus Vacation

This is not to be confused with the console exclusive game Dead or Alive Xtreme
3: Venus. This is a free to play casual volleyball *management* game, and lacks
the volleyball gameplay or minigames of its console counterpart and has no
English translation, but - at least it is on PC. For help with installing this
game and understanding some of the gameplay, refer to this article (the camera
mode of the Google Translate Android app may also be helpful for any steps that
have changed since this article was written):

https://www.dualshockers.com/dead-alive-xtreme-venus-vacation-guide/

Fixed
-----
- Lights & shadows
- Water
- HUD

Installing
----------
1. Extract the contents of the zip file to the game directory.

2. In the launcher (not the game), open settings (2nd button from the top) and
   change everything to the left-most option (this is what I tested on - other
   options may or may not work).

3. **IMPORTANT: Once the main game launches, press F7 to switch to exclusive
   full screen mode to engage 3D. Repeat this anytime you alt+tab out of the
   game to re-engage 3D.**

Compatibility with third party Modding Tools
--------------------------------------------
I am aware that some players will wish to use this in conjunction with other
modding tools to take the fan service further than the developers intended.
This should be possible, but is not something I have personally tried and I
cannot guarantee whether or not it will work. You may try naming 3DMigoto
d3d11.dll and using the proxy_d3d11 option to load the third party modding tool
after 3DMigoto, or if the third party tool has a similar option you may be able
to do the reverse.

Side-by-Side / Top-and-Bottom Output Modes
------------------------------------------
This fix is bundled with the SBS / TAB output mode support in 3DMigoto. To
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
