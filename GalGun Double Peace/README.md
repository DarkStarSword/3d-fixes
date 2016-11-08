Gal\*Gun: Double Peace
======================

Fixes
-----
- Various automatic HUD depth adjustments (refer to Keys below)
- Shadows
- God Rays

Installation
------------
Extract the zip file under:

    ....\GalGun Double Peace\Binaries\Win64

Open GalGun Double Peace\Engine\Config\BaseEngine.ini and search for:

    AllowNvidiaStereo3d=False

Change it to True:

    AllowNvidiaStereo3d=True

Keys
----
~ = Toggle between two convergence presets
1 = HUD to 2D screen depth (use for menus)
2 = HUD to first vertex depth (selected by default, recommended for gameplay)
3 = HUD to individual vertex depth (like 2, but HUD elements may be more skewed)
4 = HUD to mouse depth (Periodically move the mouse to all four sides to calibrate)
5 = HUD to depth at screen center
