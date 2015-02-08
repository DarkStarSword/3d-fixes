Miasmata
========

I'd like to present a game that is pretty special to me. I first played it (in
2D) back in 2012 not long after it came out, and I had quite an amazing
experience in it - something which I have never quite felt in a game before and
honestly don't know if I ever will again. This is a very unique survival
exploration game that gives you a map and compass and a realistic cartography
system, but it really starts to get interesting once you get lost, and believe
me - you *will* get lost (and if you don't - you're doing it wrong).

<table><tr><td>
<iframe  src="http://photos.3dvisionlive.com/e/embed/54d627fee7e564f3040000fb/nvidia/480.294/important" width="480" height="294" frameborder="1" vspace="0" hspace="0" marginwidth="0" marginheight="0" scrolling="no" noresize><p>See stereo 3D on <a href="http://photos.3dvisionlive.com">photos.3dvisionlive.com</a></p></iframe>
</td><td>
<iframe  src="http://photos.3dvisionlive.com/e/embed/54d62d17e7e564543200017c/nvidia/480.294/important" width="480" height="294" frameborder="1" vspace="0" hspace="0" marginwidth="0" marginheight="0" scrolling="no" noresize><p>See stereo 3D on <a href="http://photos.3dvisionlive.com">photos.3dvisionlive.com</a></p></iframe>
</td></tr></table>

There's something about the tension that this game creates when you suddenly
realise that you are no longer on the path you were following and aren't really
certain which way you came from. When the sun goes down while you are lost in
the wilderness and you discover that this developer actually made night *dark*
in this game and you can't see two meters in front of your face. When your
heart starts beating as you suddenly realise that you are no longer alone...

<div style="text-align: center;">
<iframe  src="http://photos.3dvisionlive.com/e/embed/54d62142e7e5648f2e000175/nvidia/500.300/important" width="500" height="300" frameborder="1" vspace="0" hspace="0" marginwidth="0" marginheight="0" scrolling="no" noresize><p>See stereo 3D on <a href="http://photos.3dvisionlive.com">photos.3dvisionlive.com</a></p></iframe>
</div>

I wrote a [short story about my first day in this game][1], which goes over
some of the basics of the game in a bit more detail.

[1]: http://steamcommunity.com/app/223510/discussions/0/540741131417338368/#c540741131521570753

This game has been fixed for 3D before - 3d4dd did an excellent job in making
it playable in 3D, and it was in fact [his fix][2] that prompted my second
playthrough of the game, which later led to me getting involved with modding
the game before I took up 3D fixing. I released an [unofficial community
patch][3] to fix some of the bugs in the game, an [achievement tracker][4] to
help out completionists with some of the harder or broken achievements, a
[modding tool][5] to tweak some of the game's parameters, and even helped Gooby
to [translate the game into French][6]. One of my long standing goals of
learning how to fix 3D in games has been to come back to this one and solve the
last few remaining issues - achievement unlocked ;-)

[2]: http://helixmod.blogspot.com.au/2012/12/miasmata.html
[3]: http://steamcommunity.com/app/223510/discussions/0/648812916771880184/
[4]: http://steamcommunity.com/app/223510/discussions/0/648813728501354813/
[5]: http://steamcommunity.com/app/223510/discussions/0/630800445647188169/
[6]: http://steamcommunity.com/app/223510/discussions/0/540741859566627042/

<table><tr><td>
<iframe  src="http://photos.3dvisionlive.com/e/embed/54d64f41e7e564f22e000191/nvidia/480.294/important" width="480" height="294" frameborder="1" vspace="0" hspace="0" marginwidth="0" marginheight="0" scrolling="no" noresize><p>See stereo 3D on <a href="http://photos.3dvisionlive.com">photos.3dvisionlive.com</a></p></iframe>
</td><td>
<iframe  src="http://photos.3dvisionlive.com/e/embed/54d64fc0e7e5646d0d0001ad/nvidia/480.294/important" width="480" height="294" frameborder="1" vspace="0" hspace="0" marginwidth="0" marginheight="0" scrolling="no" noresize><p>See stereo 3D on <a href="http://photos.3dvisionlive.com">photos.3dvisionlive.com</a></p></iframe>
</td></tr></table>


Fixed
-----

### Medium & High quality Water ###

I managed to fix the real-time reflections when the water quality is set to
medium or high, and as you can see the reflections are accurately rendered
below the surface where they belong:

<table><tr><td>
<iframe  src="http://photos.3dvisionlive.com/e/embed/54d62b4ae7e5646803000108/nvidia/480.294/important" width="480" height="294" frameborder="1" vspace="0" hspace="0" marginwidth="0" marginheight="0" scrolling="no" noresize><p>See stereo 3D on <a href="http://photos.3dvisionlive.com">photos.3dvisionlive.com</a></p></iframe>
</td><td>
<iframe  src="http://photos.3dvisionlive.com/e/embed/54d62543e7e5643530000170/nvidia/480.294/important" width="480" height="294" frameborder="1" vspace="0" hspace="0" marginwidth="0" marginheight="0" scrolling="no" noresize><p>See stereo 3D on <a href="http://photos.3dvisionlive.com">photos.3dvisionlive.com</a></p></iframe>
</td></tr></table>

Note - the water rendering gets messed up after changing any graphics settings
in the game, so be sure to restart the game to fix it!

### Light Shafts ###

The light shafts were a bit tricky, requiring a correction in world-space
coordinates without the necessary matrices to do so. As a last resort I ended
up using an unrelated object's MVP matrix and was able to calculate the correct
adjustment from that.

Then I hit a snag - I'm sure everyone reading this will be aware of the issue
in 3D where objects will disappear at the edge of the screen. Well, after
fixing the light shafts the same thing happened to the fog, which looked
incredibly jarring and eye-bleeding. I ended up interpolating the fix away at
the edge of the screen to prevent this from happening, which gives a very good
result.

<table><tr><td>
<iframe  src="http://photos.3dvisionlive.com/e/embed/54d6284ae7e564b0060000f2/nvidia/480.294/important" width="480" height="294" frameborder="1" vspace="0" hspace="0" marginwidth="0" marginheight="0" scrolling="no" noresize><p>See stereo 3D on <a href="http://photos.3dvisionlive.com">photos.3dvisionlive.com</a></p></iframe>
</td><td>
<iframe  src="http://photos.3dvisionlive.com/e/embed/54d653abe7e564ee090001b9/nvidia/480.294/important" width="480" height="294" frameborder="1" vspace="0" hspace="0" marginwidth="0" marginheight="0" scrolling="no" noresize><p>See stereo 3D on <a href="http://photos.3dvisionlive.com">photos.3dvisionlive.com</a></p></iframe>
</td></tr></table>

### Automatic Stereo Crosshair ###

This is something I've been wanting to try out for a while now - using the
depth buffer to automatically determine the correct depth to place the
crosshair in the game. This won't work in every game and takes a bit of effort
to get working, but it was extremely effective in this game once I got the
maths right.

<table><tr><td>
<iframe  src="http://photos.3dvisionlive.com/e/embed/54d64e49e7e564ee090001b6/nvidia/480.294/important" width="480" height="294" frameborder="1" vspace="0" hspace="0" marginwidth="0" marginheight="0" scrolling="no" noresize><p>See stereo 3D on <a href="http://photos.3dvisionlive.com">photos.3dvisionlive.com</a></p></iframe>
</td><td>
<iframe  src="http://photos.3dvisionlive.com/e/embed/54d64e8be7e5645432000193/nvidia/480.294/important" width="480" height="294" frameborder="1" vspace="0" hspace="0" marginwidth="0" marginheight="0" scrolling="no" noresize><p>See stereo 3D on <a href="http://photos.3dvisionlive.com">photos.3dvisionlive.com</a></p></iframe>
</td></tr></table>

It is still a bit experimental, so two fixed depths can be cycled by pressing
the 9 key if needed. Pressing 9 again will return to the auto crosshair.

### Other Fixes ###

- A halo on the water is fixed such that it is no longer necessary to use the
  Aion profile.

- Sky box depth pinned at infinity, allowing the convergence to be customised
  if desired.

- A seam on the horizon has been fixed (provided medium or high quality water
  is selected), though if you do manage to get right up close to the edge of
  the map the Truman wall will become apparent.

- Updated to latest Helix Mod.


Installation
------------

- [Download the fix here][7]

[7]: https://s3.amazonaws.com/DarkStarSword/3Dfix-Miasmata-2015-02-09.zip

- If you have assigned Miasmata to the Aion profile for the previous version of
  this fix, remove it from that profile.

- Unpack the zip file to the game directory, e.g.

    ...\Steam\SteamApps\common\Miasmata

- Recommended: Install the [unofficial communtiy patch][8], which fixes a
  number of bugs in the base game.

[8]: http://steamcommunity.com/app/223510/discussions/0/648812916771880184/

- Set water quality to high to enable real-time 3D reflections. Medium is ok as
  well, but do not use low quality.

- Set Antialiasing to high (makes a huge difference to the water quality)

- **IMPORTANT: Restart the game**. Do this any time you change the graphics
  quality settings!


Known Issues
------------

- **IMPORTANT**: Sometimes triangulating a landmark doesn't work properly in 3D
  (it's being falsely obscured by something else to the left). When this
  happens hold the Q button to temporarily reduce separation to the minimum
  which will allow triangulation to work. Disabling 3D will also work, but the
  Q method is much faster.

- There might be some vantage points where the stereo crosshair gets confused
  while looking out towards the horizon. If this happens press 9 to cycle to a
  fixed crosshair depth (press twice more to return to the auto crosshair).

- Changing the graphics settings will mess up the water - restart the game
  after changing any graphics settings!


Bugs
----

<div style="text-align: center;">
<iframe  src="http://photos.3dvisionlive.com/e/embed/54d62c87e7e5648106000102/nvidia/500.300/important" width="500" height="300" frameborder="1" vspace="0" hspace="0" marginwidth="0" marginheight="0" scrolling="no" noresize><p>See stereo 3D on <a href="http://photos.3dvisionlive.com">photos.3dvisionlive.com</a></p></iframe>
</div>

These are not bugs specifically related to the 3D - these are just four common
bugs that everyone seems to hit. None of them are game breaking, but it's handy
to know ahead of time how to work around them.

1. At night if you are holding a torch in your right hand and open your map or
   journal, the light will go out making it near impossible to see. If your
   hand is empty your lighter will work properly, so it's often a good idea to
   stand near some sticks and throw away whatever you are holding before
   getting out your map.

2. Opening and closing the map too quickly when standing next to a known
   landmark or under the effect of a mental clarity tonic the mouse input will
   lock up. If that happens use tab to open and close your journal to restore
   the mouse.

3. Researching a plant that has previously been researched will open the
   journal to the front page instead of the research notes. Doing this will
   have caused the note to move to the very end of your research list, so it is
   still pretty easy to find even if you can't remember the plant's name.

4. As already mentioned several times, changing the graphics quality settings
   you cause a "grainy water" rendering issue until the game is restarted.

Update 2015-02-09
-----------------

- Fixed black seam that could appear at the edge of the map if the camera was
  tilted (such as during the ending cutscene).

- Fix will now work with older versions of the game, such as the v2.0.0.4
  version from GOG. Note that this old version was only tested with all
  graphics settings set to high, and the fog/god rays have clipping issues on
  this version, so it is recommended to update.
