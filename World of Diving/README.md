World of Diving
===============

Fixed
-----
- Many halos fixed in the first level.
- Unity Light and Shadows fixed.
- Sun depth no longer varies with convergence and is pinned at an appropriate
  depth.

Keys
----
- Use number row to adjust UI depth (tilde: 0%, 1-9 sets 10% multiples, 0: 100%)

Known Issues
------------
- Levels other than the first are pretty much unplayable. Mostly a matter of
  hunting down the surface vertex shaders and applying the same fix to them.
- Refraction through bubbles is incorrect
- Mouse cursor depth cannot be adjusted (press tilde when in a menu to bring
  the UI to screen depth)
