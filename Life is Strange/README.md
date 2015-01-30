Life is Strange
===============

Fixed
-----
- Fog
- Glow around sun

Installation
------------
1. Unpack the zip file under:

    ...\SteamApps\common\Life Is Strange\Binaries\Win32

2. Open this file in a text editor:

    ...\SteamApps\common\Life Is Strange\Engine\Config\BaseEngine.ini

Scroll down about 20% to find the line:

    AllowNvidiaStereo3d=True

And change it to:

    AllowNvidiaStereo3d=False

No, you didn't misread that - you need to **DISABLE** Unreal Engine's built in 3D
Vision support, as it causes halos on effects that were otherwise working (it
seems that many shaders in Unreal may have recently changed to use the vPos
semantic, which does not need a stereo correction).
