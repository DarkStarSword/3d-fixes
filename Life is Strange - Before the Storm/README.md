Life is Strange - Before the Storm
==================================

The long awaited support for Unity 5.5 (and higher) in my Unity template has
finally arrived!

We're all used to game and engine updates breaking these fixes from time to
time and when it happens it ranges from a minor inconvenience requiring just a
few minutes or hours to address, to a massive time waste of having to redo an
entire fix from scratch, to a major headache where the new version has
fundamentally changed in some way requiring a huge amount of new work put in to
solve some new problem that didn't exist before. The Unity 5.5 update was of
the later variety due to some major changes in the engine's shader format, but
I have at last managed to decipher the new format and we can now enjoy modern
Unity games in stereo 3D once again, beginning with the prequel to one of my
favourite games of all time :)

Auto-Convergence
----------------
This fix introduces a brand new feature to automatically adjust the convergence
while playing to suit the wide range of camera angles this game has. This
feature tries to always maintain a small amount of pop-out to maximise the 3D
effect, while preventing excessive popout that could make the scene
uncomfortable to view and lowering the convergence when necessary to prevent
objects near the camera from obscuring the view of the game.

The auto-convergence feature replaces the traditional meaning of 3D Vision's
convergence setting with a "popout" setting, which is similar to convergence,
but gives better results with a wider range of camera angles, monitor sizes and
viewing distances. The same keys that normally adjust the convergence will
adjust the popout instead when auto-convergence is enabled, and the popout
value will be displayed on screen while adjusting it.

This feature has a number of tunable parameters, which can be tweaked by
editing the [Constants] section in the d3dx.ini. These tunables include things
such as the initial popout, minimum and maximum allowable convergence values,
thresholds for how far the convergence is allowed to get away from the target,
and anti-judder countermeasures.

- ~: Toggle auto-convergence feature on and off
- Ctrl+F5: Reduce popout when auto-convergence is on
- Ctrl+F6: Increase popout when auto-convergence is on

Installation
------------

1. Extract the contents of the zip file to the game directory.

2. Right click on the game in Steam and go to "Properties" -> "Set Launch
   Options" and enter "-window-mode exclusive" (without the quotes) and click
   "Ok"

3. I suggest disabling subtitles, as these are a little distracting.

Known Issues
------------
- Activating the SBS/TAB shader will crash the game.
- In some scenes an object obscuring the camera in only the left eye will fail
  to trigger auto-convergence to move it out of the way. Fixing this would lead
  to the same crash plaguing the SBS/TAB shader in this game.

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

[4]: https://github.com/bo3b/3Dmigoto/blob/master/AUTHORS.txt
