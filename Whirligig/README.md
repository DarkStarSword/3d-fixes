Whirligig
=========

This is a proof of concept of using 3DMigoto to convert a side-by-side
application into 3D Vision.

The Whirligig VR video player is intended to be used with the Rift, and while
it can be run with 3D Vision Automatic, the stereo video feeds are lost leaving
a flat video on a spherical screen some distance from the camera.

Use the provided 'Whirligig - SBS.bat' file to launch Whirligig in side-by-side
mode, then 3DMigoto will take over and convert it to 3D Vision via a custom
shader, which will preserve the 3D video streams.

This approach works, but has a major problem that Whirligig disables mouse look
because it thinks VR is enabled. J + K will rotate the camera, but tilt can
only be performed via the menu.

Convergence should be set to 0 (or at least quite low) to prevent distortion
from 3D Vision (this will not eliminate VR distortion) - the 3D effect will
still be present as it comes from the 3D video stream, not 3D Vision.
The separation control may then be used to adjust where "infinity" on the video
is placed as a sort of parallax control.

The ; (semicolon) key will set convergence to 0 and toggle between minimum and
maximum separation.

The ' (quote) key will zoom in to a region of the video less affected by VR
distortion, but in doing so will crop the video.
