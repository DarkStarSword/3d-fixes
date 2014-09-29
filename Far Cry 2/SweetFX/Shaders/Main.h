   /*-----------------------------------------------------------.   
  /                 Defining constants                          /
  '-----------------------------------------------------------*/

//These values are normally defined by the injector dlls, but not when anylyzed by GPU Shaderanalyzer
//I need to ensure they always have a value to be able to compile them whenever I'm not using the injector.
#ifdef SMAA_PIXEL_SIZE
  #ifndef BUFFER_RCP_WIDTH
    #define BUFFER_RCP_WIDTH SMAA_PIXEL_SIZE.x
    #define BUFFER_RCP_HEIGHT SMAA_PIXEL_SIZE.y
    #define BUFFER_WIDTH (1.0 / SMAA_PIXEL_SIZE.x)
    #define BUFFER_HEIGHT (1.0 / SMAA_PIXEL_SIZE.y)
  #endif
#endif

#ifndef BUFFER_RCP_WIDTH
  #define BUFFER_RCP_WIDTH (1.0 / 1680)
  #define BUFFER_RCP_HEIGHT (1.0 / 1050)
  #define BUFFER_WIDTH 1680
  #define BUFFER_HEIGHT 1050
#endif

#define screen_size float2(BUFFER_WIDTH,BUFFER_HEIGHT)

#define px BUFFER_RCP_WIDTH
#define py BUFFER_RCP_HEIGHT

#define pixel float2(px,py)

// -- Define DirectX9 specific aliases --
#if SMAA_HLSL_3 == 1
  #define myTex2D(s,p) tex2D(s,p)
  
  #define s0 colorTexG
  #define s1 colorTexG //TODO make a nearest sampler if needed
#endif

// -- Define DirectX10/11 specific aliases --
#if SMAA_HLSL_4 == 1 || SMAA_HLSL_4_1 == 1
  #define myTex2D(s,p) s.SampleLevel(LinearSampler, p, 0)

  #define s0 colorTexGamma
  #define s1 colorTexGamma //TODO make a nearest sampler if needed
#endif

   /*-----------------------------------------------------------.   
  /                 Including enabled shaders                   /
  '-----------------------------------------------------------*/


#if (USE_LUMASHARPEN == 1)
    #include "SweetFX\Shaders\LumaSharpen.h"
#endif

#if (USE_HDR == 1)
    #include "SweetFX\Shaders\HDR.h"
#endif

#if (USE_BLOOM == 1)
    #include "SweetFX\Shaders\Bloom.h"
#endif

#if (USE_TECHNICOLOR == 1)
    #include "SweetFX\Shaders\Technicolor.h"
#endif

#if (USE_DPX == 1)
    #include "SweetFX\Shaders\DPX.h"
#endif

#if (USE_LIFTGAMMAGAIN == 1)
	#include "SweetFX\Shaders\LiftGammaGain.h"
#endif

#if (USE_TONEMAP == 1)
    #include "SweetFX\Shaders\Tonemap.h"
#endif

#if (USE_SEPIA == 1)
    #include "SweetFX\Shaders\Sepia.h"
#endif

#if (USE_VIBRANCE == 1)
    #include "SweetFX\Shaders\Vibrance.h"
#endif

#if (USE_CURVES == 1)
    #include "SweetFX\Shaders\Curves.h"
#endif

#if (USE_VIGNETTE == 1)
    #include "SweetFX\Shaders\Vignette.h"
#endif

#if (USE_DITHER == 1)
    #include "SweetFX\Shaders\Dither.h"
#endif

#if (USE_SPLITSCREEN == 1)
    #include "SweetFX\Shaders\Splitscreen.h"
#endif


   /*-----------------------------------------------------------.   
  /                        Effect passes                        /
  '-----------------------------------------------------------*/

float4 main(float2 tex, float4 FinalColor)
{
//    FinalColor.rgb = (FinalColor.rgb <= 0.03928) ? FinalColor.rgb / 12.92 : pow( (FinalColor.rgb + 0.055) / 1.055, 2.4 ); // SRGB to Linear


    // Linear to SRGB gamma correction. Needed here because SMAA uses linear for it's final step while the other shaders use SRGB.
    #if (USE_SMAA_ANTIALIASING == 1)
    FinalColor.rgb = (FinalColor.rgb <= 0.00304) ? FinalColor.rgb * 12.92 : 1.055 * pow( FinalColor.rgb, 1.0/2.4 ) - 0.055; // Linear to SRGB
	#endif

	// LumaSharpen (has to be the first pass because it samples multiple texels)
    #if (USE_LUMASHARPEN == 1)
		FinalColor = LumaSharpenPass(FinalColor,tex);
	#endif
	
	// Bloom
    #if (USE_BLOOM == 1)
		FinalColor = BloomPass (FinalColor,tex);
	#endif
	
	// HDR
    #if (USE_HDR == 1)
		FinalColor = HDRPass (FinalColor,tex);
	#endif
	
	// Technicolor
    #if (USE_TECHNICOLOR == 1)
		FinalColor = TechnicolorPass(FinalColor);
	#endif
	
	// DPX
    #if (USE_DPX == 1)
		FinalColor = DPXPass(FinalColor);
	#endif
	
	// Lift Gamma Gain
    #if (USE_LIFTGAMMAGAIN == 1)
		FinalColor = LiftGammaGainPass(FinalColor);
	#endif
	
	// Tonemap
	#if (USE_TONEMAP == 1)
		FinalColor = TonemapPass(FinalColor);
	#endif
	
	// Vibrance
	#if (USE_VIBRANCE == 1)
		FinalColor = VibrancePass(FinalColor);
	#endif
	
	// Curves
	#if (USE_CURVES == 1)
		FinalColor = CurvesPass(FinalColor);
	#endif
	
	// Sepia
	#if (USE_SEPIA == 1)
    FinalColor = SepiaPass (FinalColor);
	#endif
	
	// Vignette
	#if (USE_VIGNETTE == 1)
		FinalColor = VignettePass(FinalColor,tex);
	#endif

	// Dither (should go last as it only dithers what went before it)
	#if (USE_DITHER == 1)
		FinalColor = DitherPass(FinalColor,tex);
	#endif
	
	// Splitscreen
	#if (USE_SPLITSCREEN == 1)
		FinalColor = SplitscreenPass(FinalColor,tex);
	#endif
	
  // SRGB to Linear gamma correction. (Hmm should this go after Dither? .. TODO: investigate)
  #if (USE_SMAA_ANTIALIASING == 1 && SMAA_HLSL_3 != 1) //Only for DirectX 10/11
    FinalColor.rgb = (FinalColor.rgb <= 0.03928) ? FinalColor.rgb / 12.92 : pow( (FinalColor.rgb + 0.055) / 1.055, 2.4 ); // SRGB to Linear
	#endif



	// Return FinalColor
	return FinalColor;
}
