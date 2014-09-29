

 .--------------------------------------------------.
 
          .-.                   .  .---..   .
         (   )                 _|_ |     \ / 
          `-..  .    ._.-.  .-. |  |---   /  
         (   )\  \  / (.-' (.-' |  |     / \ 
          `-'  `' `'   `--' `--'`-''    '   '
                    Shader Suite
                    by CeeJay.dk                    
 '--------------------------------------------------'
 
 - Version 1.3

SweetFX is a universal image improvement and tweaking mod,
that works with almost any 32bit DirectX 9, 10 or 11 game or application.

It's goal it provide similar tools to games in realtime, as video processing software provides for movies and videos.

Effects included:

* SMAA Anti-aliasing : Anti-aliases the image using the SMAA technique - see http://www.iryoku.com/smaa/
* LumaSharpen : Sharpens the image, making details easier to see
* Bloom : Makes strong lights bleed their light into their surroundings
* HDR : Mimics an HDR tonemapped look
* Technicolor : Makes the image look like it was processed using a three-strip Technicolor process - see http://en.wikipedia.org/wiki/Technicolor
* Cineon DPX : Makes the image look like it was converted from film to Cineon DPX. Can be used to create a "sunny" look.
* Lift Gamma Gain : Adjust brightness and color of shadows, midtones and highlights (avoids clipping)
* Tonemap : Adjust gamma, exposure, saturation, bleach and defog. (may cause clipping)
* Vibrance : Intelligently saturates (or desaturates if you use negative values) the pixels depending on their original saturation.
* Curves : Contrast adjustments using S-curves.
* Sepia : Sepia tones the image - see http://en.wikipedia.org/wiki/Sepia_tone#Sepia_toning
* Vignette : Darkens the edges of the image to make it look more like it was shot with a camera lens. - see http://en.wikipedia.org/wiki/Vignetting )
* Dither : Applies dithering to simulate more colors than your monitor can display. This lessens banding artifacts - see http://en.wikipedia.org/wiki/Dithering#Digital_photography_and_image_processing )
* Splitscreen : Enables the before-and-after splitscreen comparison mode.

You can find new releases of SweetFX in it's thread on the Guru3d forums :
http://forums.guru3d.com/showthread.php?t=368880


   /*-----------------------------------------------------------.   
  /                      Installation                           /
  '-----------------------------------------------------------*/

1) Extract or copy all the files into the directory of a game exe (keeping the file structure intact).

The installed files are:
   d3d9.dll                 - DirectX 9 proxy dll that will inject shaders into DirectX 9 games
   d3d9.fx                  - DirectX 9 specific shader code
   dxgi.dll                 - DirectX 10/11 proxy dll that will inject shaders into DirectX 10/11 games
   dxgi.fx                  - DirectX 10/11 specific shader code
   injector.ini             - Settings for the shader injector dlls - you can reconfigure the keys used in this file
   SweetFX readme.txt       - This readme
   SweetFX_preset.txt       - You can choose which settings file to load here - default is to load SweetFX_settings.txt
   SweetFX_settings.txt     - SweetFX settings. Effects can be turned on and off here, and their settings can be tweaked.
   
   SweetFX/ (directory)     - The SweetFX subdirectory. All the shaders, except d3d9.fx and dxgi.fx are stored here.
   |- /Presets/             - Presets are stored here.
   '- /Game_Compability.txt - Can't make SweetFX work with a game? - You can find help here.

   log.log                  - This logfile is not installed, but will be created when the DirectX proxy dll runs.
                              If something goes wrong, this file will usually tell you why.

Some games require special attention - You can find a list of those and instructions on how to get them working with SweetFX 
in SweetFX/Game_Compability.txt
If you encounter a game not in the list that requires more effect to work with SweetFX, post about it in the official thread
on Guru3d : http://forums.guru3d.com/showthread.php?t=368880
                            
2) Install the latest DirectX update if you haven't already
   Last I looked it was here : http://www.microsoft.com/en-us/download/details.aspx?id=35
   (You don't need any of the other stuff Microsoft tries to push - just DirectX)                            



   /*-----------------------------------------------------------.   
  /                          Usage                              /
  '-----------------------------------------------------------*/
  
It will automatically run when you start the DirectX 9, 10 or 11 game that you added SweetFX to.
If you want to run different game with SweetFX then you need to install to that games directory too.

It does not modify any game files either on disk or in memory.
Instead it uses a custom Direct3D runtime dll which the most DirectX games will call.

PRINTSCRN saves a screenshot named ScreenshotXXXX.bmp in the directory you installed SweetFX to.
SCROLL_LOCK switches it ON and OFF. It starts in ON mode.
PAUSE reloads the shader files (this is useful when you need to tweak the settings while the game is running)

Keys can be reconfigured in the injector.ini file.

Some keyboards (mostly on laptops) don't have a dedicated SCROLL_LOCK button,
but require you to hold down the Fn button while you press another key to activate Scroll Lock.

If you can't figure out the right combination just from looking at your keyboard and experimenting,
then read the documentation for your keyboard or just reconfigure the keys in injector.ini


   /*-----------------------------------------------------------.   
  /                      Tweaking settings                      /
  '-----------------------------------------------------------*/

You can choose which effects to enable, and set their parameters
in the SweetFX_settings.txt file - this can even be done while the game is running.

1) Switch away from your game with ALT+TAB or WIN+TAB
2) Open SweetFX_settings.txt in any text editor - fx. : Notepad (I use Notepad2)
3) Edit the settings and save.
4) Switch back to your game with ALT+TAB or WIN+TAB
5) If the game is running in fullscreen mode then it will now have reloaded the shader files
   and your new settings have been applied.
   If the game is running in Windowed mode then you need to press the PAUSE key to reload the shader files
   and apply your new settings.
   
And naturally you don't have to start the game before you edit your settings.
It can be done before the game runs as well.   


   /*-----------------------------------------------------------.   
  /                          Presets                            /
  '-----------------------------------------------------------'/
SweetFX has a preset feature. Presets are just settings files made for a specific game, series of games or a special purpose.
Many (most) of these are made by the users of SweetFX.

I include some of these in /SweetFX/Presets/

They are a good start if you need help finding the settings that are just right for you.

The preset feature works like this:
1) SweetFX looks in SweetFX_preset.txt , which tells it what settings file to include (load)
2) It then includes (loads) those settings.

Per default the contents of SweetFX_preset.txt is a single command:
#include "SweetFX_settings.txt"

This tells SweetFX to load the settings in SweetFX_settings.txt

To load different settings simply point to a preset.

Fx. to use the awesome Torchlight2_TFL.txt preset by TFL that is intended to make Torchlight 2 look,
darker, dirtier, grittier and all-around more "evil" simply change the #include line to :
#include "SweetFX/Presets/Torchlight2_TFL.txt"

Note that although presets are often intended for a single specific game, they can be used in any game you wish.

To make your own preset simply copy the SweetFX_settings.txt file, rename it whatever you'd like, and point the #include line to its location

For example :
1) Make a copy
2) Rename it mycustom_preset.txt
3) Move it to the Presets folder (you don't HAVE to do this - this is just to keep the files organized)
4) Change the #include line to :

#include "SweetFX/Presets/mycustom_preset.txt"

If you make a really good preset please share it with other users in the SweetFX release thread at :
http://forums.guru3d.com/showthread.php?t=368880

Similar to the other presets try also to include some details about your preset

Game: What game(s) you made this for
SweetFX version: What SweetFX version you made this for
Author: Your name
Description: "Your description goes here"
Showcase: Have screenshots or a video that showcases your preset? - put a link here.


   /*-----------------------------------------------------------.   
  /                         Problems?                           /
  '-----------------------------------------------------------*/

When the mod starts it creates a log.log file next to it's own location.
Open the log with a text editor and see what the problem is.

If no log file is created then the mod did not start.
- Maybe you didn't put the files in the right location?
- Or maybe the game doesn't use DirectX?

Most games use DirectX 9, 10 or 11.
Notable games that use OpenGL (which SweetFX doesn't work with) are all games by id software,
and those games based on their 3D engines.


Q: It says d3dx9_43.dll is missing
A: You need the latest DirectX 9 update.
   See step 2) of the installation section.
   
Q: It does not run with the 64bit version of my game exe.
A: SweetFX is not compatible with 64bit versions of games - use a 32bit version.

Q: My game crashes with SweetFX installed.
A: The log.log file will most likely tell you why.
   If no log file is created but it still crashes with SweetFX installed and not without, then it's likely crashing because it can't write to the log file.
   This is usually caused by insufficient user permissions in the game folder you installed SweetFX to.
   
   Try running the game as an administrator or change the folder permissions to grant your user account write access.
   
   This issue is mostly seen on Windows Vista, 7 and 8 with games that install to the program files folder, since Vista, 7 and 8 normally restricts write access to that folder.
   User accounts on Windows XP usually have administrator rights and don't see such problems (however letting user accounts have administrator rights can be a security risk
   which is why Microsoft changed that beginning with Vista).

Q: I don't see any change in the image
A: Try turning off anti-aliasing in the game (not in the mod)
   The mod is not compatible with some antialias implementations.
   It might be made compatible by setting compability flags.
   
   If not then you can always use the included SMAA anti-aliasing.

   
Q: How do I make MSI Afterburner / EVGA Precision / Rivatuner OSD work with this mod?
A: To make MSI Afterburner work with this mod and others like it you need to :

1) Update to the latest version of MSI Afterburner.
2) Start MSI Afterburner.
3) Switch to the "MSI On-Screen Display Server" window.
4) Create a new profile for your game and change to it.
5) Click the big wrench icon to change advanced settings.
6) Go to General -> Compatibility properties and turn on "Enable compatibility with modified Direct3D runtime libraries".

MSI Afterburner is now compatible with shader mods.

You can also change the setting for the Global profile,
but MSI does not recommend this because it might prevent some Direct3D applications from starting.

The same (very similar) steps also work with EVGA Precision and Rivatuner OSD,
as all 3 tools are based on Rivatuner OSD.


Q: How do I use SweetFX with ENBseries?
A: By making ENB run SweetFX. You need to: 

1) Rename d3d9.dll to sweetfx_d3d9.dll
2) Install the ENB series files into the same directory
3) Edit enbseries.ini so the top section looks like this:

[PROXY]
EnableProxyLibrary=true
InitProxyFunctions=true
ProxyLibrary=sweetfx_d3d9.dll

That should do it.

Q: How do I use SweetFX with OpenGL games?
A: SweetFX only supports DirectX 9 , 10 and 11 games, however you can use a OpenGL to DirectX wrapper.

Try the QindieGL wrapper : http://code.google.com/p/qindie-gl/
It can translate OpenGL calls to DirectX 9 calls that SweetFX will work with.
It does not work with all OpenGL games and some games it does work with will have buggy graphics
and it will likely run slower since it's being translated, but if you want to try out SweetFX with OpenGL games this is probably your best bet.
I haven't tried it myself yet so let me know if it works or not.

Q: How do I use SweetFX with DirectX 8 games?
A: SweetFX only supports DirectX 9 , 10 and 11 games, however you can use a DirectX 8 to DirectX 9 wrapper.

Try the DX8 to DX9 convertor from ENBseries : http://enbdev.com/download_en.htm
Let me know if it works for you.

Q: How do I use SweetFX with games that use DirectX 7 or older or even Glide?
A: Again you need to find a wrapper that will translate the API that the game uses to one that SweetFX supports.


   /*-----------------------------------------------------------.   
  /                     Uninstallation                          /
  '-----------------------------------------------------------*/

1) Delete all the files you copied during the installation.


   /*-----------------------------------------------------------.   
  /                       Changelog                             /
  '-----------------------------------------------------------*/

Version 1.3
    Adds the Lift Gamma Gain shader which lets users adjust brightness and color of shadows, midtones and highlights.
    Adds the Curves shader which uses S-curves to adjust the contrast of the image
    Adds the Splitscreen shader which makes it easier to do comparison screenshots and videos.
    Reversed the DPX blend setting so smaller numbers now mean less effect and not more (it's more logical this way)
    Better default DPX settings
    More conservative default Vibrance settings (down from 0.20 to 0.15)
    All settings in the settings file now have ranges. (preperations for an upcomming GUI)

Version 1.2
    Fixes a rounding problem on AMD hardware with the dither shader.
    Includes usermade presets - look in the SweetFX/Presets/ folder.
    Updated and expanded documentation.
    Minor speed improvements to most of the shaders. Hopefully it adds up.
    Based on user feeedback default settings now use more conservative sharpening
    Also default settings now enable conservative Vibrance settings
    Slightly better default Sepia settings
    Vignette now more uniformly darkens all the color channels of the screen edges
    Adds the DPX shader - settings still need a lot of work though.
    
Version 1.1.1

    Fixes DirectX 10/11 support 

Version 1.1

    Keymappings have changed to Printscreen, Scroll_lock and Pause
    Settings now use a .txt suffix which is hopefully less scary for novices
    Optimized the Vignette shader to run a little faster
    Adds the Dither shader that performs dithering of the image to help remove or reduce banding artifacts (most commonly caused by the Vignette)
    Fixes and improves Vibrance
    Accidently broke DirectX 10/11 support  

Version 1.0

    First non-beta release.
    Adds SMAA, LumaSharpen, Vibrance
    Tweaks and improvements to HDR, Bloom, Tonemap, Sepia and Vignette
    SMAA is now configurable, so you can use your own settings and it even allows you to use Color Edge Detection
    Supports DX 9,10 and 11 and will automatically use the version the game requires without depending on the user to do anything 


   /*-----------------------------------------------------------.   
  /                          Credits                            /
  '-----------------------------------------------------------*/

 Uses SMAA. Copyright (C) 2011 by Jorge Jimenez, Jose I. Echevarria,
 Belen Masia, Fernando Navarro and Diego Gutierrez.
 
 Uses InjectSMAA by Andrej Dudenhefner ( mrhaandi )
 
 Uses shaders from FXAATool by Violator, [some dude], fpedace, BeetleatWar1977 and [DKT70]
 
 DPX shader by Loadus
 
 Lift Gamma Gain shader by 3an and CeeJay.dk
 
 SweetFX, LumaSharpen, Dither, Curves, Vibrance and Splitscreen by Christian Cann Schuldt Jensen ( CeeJay.dk )
 
   /*-----------------------------------------------------------.   
  /                          Contact                            /
  '-----------------------------------------------------------*/
Post comments, suggestions, support questions, screenshots, videos and presets to the official SweetFX thread at:
http://forums.guru3d.com/showthread.php?t=368880

Or email your comments and thoughts (but please no support questions - keep those to the Guru3D thread) to :
      CeeJay.dk  (at)  gmail.com 