Viscera Cleanup Detail (including Santa's Rampage & Shadow Warrior)
===================================================================

Update 2015-10-28
-----------------
Since the game has now left early access I've polished off a few things in the
fix to celebrate:

- Moved environmental reflections to infinity. Makes a dramatic visual
  improvement to some of the more shiny levels, particularly Revolutionary
  Robotics and Paintenance Tunnels.
- Better approximate fix for bloom by using the depth buffer
- Fixed bloom transparency in some places
- More accurate fix for multi-pass fog volume density (e.g. Zero-G level)
- Fixed trapdoor in office
- Adjusted Personal Identification Device' text depth (toggle with X)
- Added ] key to disable object highlight correction (in case it causes
  problems for anyone)

Fixed
-----
- UI menus and in-game screens
- Object highlights
- Molotov Cocktails (in Santa's Rampage)
- Shadows
- Light shafts
- Decals
- Bloom (using depth buffer - press H for alternate infinity adjustment)
- Fog
- Environmental reflections

Installation
------------
Extract zip file under:

    ...\Steam\SteamApps\common\Viscera\Binaries\Win32

Use the 32bit version of Viscera cleanup detail.

Do not manually adjust the separation - doing so will cause object highlights
and Molotov cocktails to become misaligned! Four separation presets are
provided on the backslash key as an alternative.

Known Issues
------------
- Some object highlights and Molotov cocktails are misaligned (to the right)
  when 3D is disabled. This appears to be a driver issue as it happens whenever
  3D is enabled in the control panel and the fix will counter this problem, but
  only while 3D is enabled and using the provided separation presets.

- If the object highlights are still misaligned with the backslash presets, try
  pressing ] to disable the correction. If neither way works, let me know.

- Some of the default nvidia key bindings affect this game, e.g. adjusting
  separation with Ctrl+F4 will freeze the physics (press F4 a second time to
  fix)
