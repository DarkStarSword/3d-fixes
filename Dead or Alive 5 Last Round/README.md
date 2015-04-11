Dead or Alive 5 Last Round
==========================

A fix by 3d4dd and DarkStarSword

Fixed
-----
- Water
- Fog & heat distortion effects
- UI depth adjusted

Installation
------------
Extract zip file under ...\Steam\SteamApps\common\Dead or Alive 5 Last Round

HUD Depth
---------
The fix pushes the HUD to 30% depth by default. To adjust this, open these
three files in a text editor:

    ShaderOverride/VertexShaders/28C9FBE7.txt
    ShaderOverride/VertexShaders/C4D72D79.txt
    ShaderOverride/VertexShaders/E0E7F85D.txt

Then find this line:

    def c222, 0, 1, 0.0625, 0.3

Set the last parameter to what you'd like. 0.3 is 30% of the way in. Set it to
-0.05 for 5% popout for example. The game must be restarted for this change to
take effect.

Known Issues
------------
- Sun flare is at wrong depth
