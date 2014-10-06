World of Diving
===============

**IMPORTANT: Use nVidia inspector to set game to use profile: Aion**

Fixed
-----
- Extreme haloing fixed
- Broken light effect disabled (green underwater lighing, cabin lighting, etc)
- Shadows (Do not adjust convergence from value chosen automatically when game is launched)

Keys
----
- Use number row to adjust UI depth (tilde: 0%, 1-9 sets 10% multiples, 0: 100%)
- Press U to disable shadows (e.g. if custom convergence is more important to you)
- Press I to turn on broken lighting shaders

Known Issues
------------
- Convergence must be set to 0 for the shadows to be at the correct depth
- Convergence must be set to 0 for the sun to appear at the correct depth
- Some surfaces still have broken shadows
- Shadows are not rendered properly at edge of screen
- Some surfaces have flickering issues (possibly due to Aion profile? Check the
  git history for an partial alternate fix, but there are a LOT of shaders that
  need fixing without it)
- Specular highlights on fish are incorrect
- Mouse cursor depth cannot be adjusted (press tilde when in a menu to bring
  the UI to screen depth)
