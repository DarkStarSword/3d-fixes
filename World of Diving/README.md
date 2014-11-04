World of Diving
===============

Fixed
-----
- Many halos fixed in the first level.
- Shadows disabled (U to toggle).
- Broken light effect disabled (green underwater lighing, cabin lighting, etc)
- Sun depth no longer varies with convergence and is pinned at an appropriate
  depth.

Keys
----
- Use number row to adjust UI depth (tilde: 0%, 1-9 sets 10% multiples, 0: 100%)
- Press U to toggle shadows
- Press I to turn on broken lighting shaders

Known Issues
------------
- Levels other than the first are pretty much unplayable. Mostly a matter of
  hunting down the surface vertex shaders and applying the same fix to them.
- Specular highlights on fish are incorrect
- Refraction through bubbles is incorrect
- Mouse cursor depth cannot be adjusted (press tilde when in a menu to bring
  the UI to screen depth)

Alternate Fix
-------------
Check the git history for an alternate fix that used the Aion profile - using
this profile fixes many of the halo issues, but introduces flickering on some
surfaces and breaks the previously working shadows. There is also a partial
shadow fix using this profile, however it requires convergence = 0, which does
not result in a very good 3D effect.
