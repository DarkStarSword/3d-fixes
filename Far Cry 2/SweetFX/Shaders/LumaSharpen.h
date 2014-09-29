/*
   _____________________
     
     LumaSharpen 1.3.12
   _____________________ 

  by Christian Cann Schuldt Jensen ~ CeeJay.dk
  
  It blurs the original pixel with the surrounding pixels and then subtracts this blur to sharpen the image.
  It does this in luma to avoid color artifacts and allows limiting the maximum sharpning to avoid or lessen halo artifacts.
  
  This is similar to using Unsharp Mask in Photoshop.
    
  Compiles with 3.0
*/

   /*-----------------------------------------------------------.   
  /                      Developer settings                     /
  '-----------------------------------------------------------*/
#define CoefLuma float4(0.2126, 0.7152, 0.0722,0)      // BT.709 & sRBG luma coefficient (Monitors and HD Television)
//#define CoefLuma float4(0.299, 0.587, 0.114,0)       // BT.601 luma coefficient (SD Television)
//#define CoefLuma float4(1.0/3.0, 1.0/3.0, 1.0/3.0,0) // Equal weight coefficient

#define sharp_strength_luma (CoefLuma * sharp_strength)

   /*-----------------------------------------------------------.   
  /                          Main code                          /
  '-----------------------------------------------------------*/
#if target == 1
float4 main( float2 tex ) // Use with Shaderanalyzer and MPC-HC
#else
float4 LumaSharpenPass(float4 inputcolor, float2 tex ) 
#endif
{

  // -- Get the original pixel --
  float4 ori = myTex2D(s1, tex);       // ori = original pixel


   /*-----------------------------------------------------------.   
  /                       Sampling patterns                     /
  '-----------------------------------------------------------*/
  //   [ NW,   , NE ] Each texture lookup (except ori)
  //   [   ,ori,    ] samples 4 pixels
  //   [ SW,   , SE ]

  // -- Pattern 1 -- A (fast) 7 tap gaussian using only 2+1 texture fetches.
  #if pattern == 1

	// -- Gaussian filter --
	//   [ 1/9, 2/9,    ]     [ 1 , 2 ,   ]
	//   [ 2/9, 8/9, 2/9]  =  [ 2 , 8 , 2 ]
 	//   [    , 2/9, 1/9]     [   , 2 , 1 ]

    float4 blur_ori = myTex2D(s0, tex + (float2(px,py) / 3) * offset_bias);  // North West
    blur_ori += myTex2D(s0, tex + (float2(-px,-py) / 3) * offset_bias); // South East

    //blur_ori += myTex2D(s0, tex + float2(px,py) / 3 * offset_bias); // North East
    //blur_ori += myTex2D(s0, tex + float2(-px,-py) / 3 * offset_bias); // South West

    blur_ori /= 2;  //Divide by the number of texture fetches
    
    sharp_strength_luma *= 1.5; // Adjust strength to aproximate the strength of pattern 2

  #endif
  
  // -- Pattern 2 -- A 9 tap gaussian using 4+1 texture fetches.
  #if pattern == 2

	// -- Gaussian filter --
	//   [ .25, .50, .25]     [ 1 , 2 , 1 ]
	//   [ .50,   1, .50]  =  [ 2 , 4 , 2 ]
 	//   [ .25, .50, .25]     [ 1 , 2 , 1 ]


    float4 blur_ori = myTex2D(s0, tex + float2(px,-py) * 0.5 * offset_bias); // South East
    blur_ori += myTex2D(s0, tex + float2(-px,-py) * 0.5 * offset_bias);  // South West    
    blur_ori += myTex2D(s0, tex + float2(px,py) * 0.5 * offset_bias); // North East
    blur_ori += myTex2D(s0, tex + float2(-px,py) * 0.5 * offset_bias); // North West

    blur_ori *= 0.25;  // ( /= 4) Divide by the number of texture fetches

  #endif 

  // -- Pattern 3 -- An experimental 17 tap gaussian using 4+1 texture fetches.
  #if pattern == 3

	// -- Gaussian filter --
	//   [   , 4 , 6 ,   ,   ]
	//   [   ,16 ,24 ,16 , 4 ]
	//   [ 6 ,24 ,   ,24 , 6 ]
	//   [ 4 ,16 ,24 ,16 ,   ]
	//   [   ,   , 6 , 4 ,   ]

    float4 blur_ori = myTex2D(s0, tex + float2(0.4*px,-1.2*py)* offset_bias);  // South South East
    blur_ori += myTex2D(s0, tex + float2(-1.2*px,-0.4*py) * offset_bias); // West South West
    blur_ori += myTex2D(s0, tex + float2(1.2*px,0.4*py) * offset_bias); // East North East
    blur_ori += myTex2D(s0, tex + float2(-0.4*px,1.2*py) * offset_bias); // North North West

    blur_ori *= 0.25;  // ( /= 4) Divide by the number of texture fetches
    
    sharp_strength_luma *= 0.51;
  #endif

  // -- Pattern 4 -- A 9 tap high pass (pyramid filter) using 4+1 texture fetches.
  #if pattern == 4

	// -- Gaussian filter --
	//   [ .50, .50, .50]     [ 1 , 1 , 1 ]
	//   [ .50,    , .50]  =  [ 1 ,   , 1 ]
 	//   [ .50, .50, .50]     [ 1 , 1 , 1 ]

    half4 blur_ori = myTex2D(s0, tex + float2(0.5 * px,-py * offset_bias));  // South South East
    blur_ori += myTex2D(s0, tex + float2(offset_bias * -px,0.5 * -py)); // West South West
    blur_ori += myTex2D(s0, tex + float2(offset_bias * px,0.5 * py)); // East North East
    blur_ori += myTex2D(s0, tex + float2(0.5 * -px,py * offset_bias)); // North North West

    //blur_ori += (2 * ori); // Probably not needed. Only serves to lessen the effect.
	
    blur_ori /= 4;  //Divide by the number of texture fetches

    sharp_strength_luma *= 0.666; // Adjust strength to aproximate the strength of pattern 2
  #endif

  // -- Pattern 8 -- A (slower) 9 tap gaussian using 9 texture fetches.
  #if pattern == 8

	// -- Gaussian filter --
	//   [ 1 , 1 , 1 ]
	//   [ 1 , 1 , 1 ]
 	//   [ 1 , 1 , 1 ]

    half4 blur_ori = myTex2D(s0, tex + float2(-px,py) * offset_bias); // North West
    blur_ori += myTex2D(s0, tex + float2(px,-py) * offset_bias);     // South East
    blur_ori += myTex2D(s0, tex + float2(-px,-py)  * offset_bias);  // South West
    blur_ori += myTex2D(s0, tex + float2(px,py) * offset_bias);    // North East
    
    half4 blur_ori2 = myTex2D(s0, tex + float2(0,py) * offset_bias); // North
    blur_ori2 += myTex2D(s0, tex + float2(0,-py) * offset_bias);    // South
    blur_ori2 += myTex2D(s0, tex + float2(-px,0) * offset_bias);   // West
    blur_ori2 += myTex2D(s0, tex + float2(px,0) * offset_bias);   // East
    blur_ori2 *= 2;

    blur_ori += blur_ori2;
    blur_ori += (ori * 4); // Probably not needed. Only serves to lessen the effect.

    // dot()s with gaussian strengths here?

    blur_ori /= 16;  //Divide by the number of texture fetches

    //sharp_strength_luma *= 0.75; // Adjust strength to aproximate the strength of pattern 2
  #endif

  // -- Pattern 9 -- A (slower) 9 tap high pass using 9 texture fetches.
  #if pattern == 9

	// -- Gaussian filter --
	//   [ 1 , 1 , 1 ]
	//   [ 1 , 1 , 1 ]
 	//   [ 1 , 1 , 1 ]

    half4 blur_ori = myTex2D(s0, tex + float2(-px,py) * offset_bias); // North West
    blur_ori += myTex2D(s0, tex + float2(px,-py) * offset_bias);     // South East
    blur_ori += myTex2D(s0, tex + float2(-px,-py)  * offset_bias);  // South West
    blur_ori += myTex2D(s0, tex + float2(px,py) * offset_bias);    // North East
    
    blur_ori += ori; // Probably not needed. Only serves to lessen the effect.
    
    blur_ori += myTex2D(s0, tex + float2(0,py) * offset_bias);    // North
    blur_ori += myTex2D(s0, tex + float2(0,-py) * offset_bias);  // South
    blur_ori += myTex2D(s0, tex + float2(-px,0) * offset_bias); // West
    blur_ori += myTex2D(s0, tex + float2(px,0) * offset_bias); // East

    blur_ori /= 9;  //Divide by the number of texture fetches

    //sharp_strength_luma *= (8.0/9.0); // Adjust strength to aproximate the strength of pattern 2
  #endif

  // -- Pattern 32 -- Comparison
  #if pattern == 32

	// -- Gaussian filter --
	//   [   , 4 , 6 ,   ,   ]
	//   [   ,16 ,24 ,16 , 4 ]
	//   [ 6 ,24 ,50 ,24 , 6 ]
 	//   [ 4 ,16 ,24 ,16 ,   ]
	//   [   ,   , 6 , 4 ,   ]

   float4 blur_ori = myTex2D(s0, tex + float2(-px,py) * 0.5 * offset_bias); // North West
    blur_ori += myTex2D(s0, tex + float2(px,-py) * 0.5 * offset_bias);  // South East
    blur_ori += myTex2D(s0, tex + float2(px,py) * 0.5 * offset_bias); // North East
  	blur_ori += myTex2D(s0, tex + float2(-px,-py) * 0.5 * offset_bias); // South West

    blur_ori /= 4;  //Divide by the number of texture fetches 

    float4 blur_ori2 = myTex2D(s0, tex + float2(-0.4*px,1.2*py) * offset_bias); // North North West
    blur_ori2 += myTex2D(s0, tex + float2(0.4*px,-1.2*py)* offset_bias);  // South South East
    blur_ori2 += myTex2D(s0, tex + float2(1.2*px,0.4*py) * offset_bias); // East North East
    blur_ori2 += myTex2D(s0, tex + float2(-1.2*px,-0.4*py) * offset_bias); // West South West
    
    blur_ori2 /= 4;

    float4 sharp = ori - blur_ori;  
   
    float sharp_luma = dot(sharp, sharp_strength_luma);
       
    float4 sharp2 = ori - blur_ori2;  
    float sharp_luma2 = dot(sharp2, sharp_strength_luma * 0.51);
    
    sharp_luma -= sharp_luma2;
    
  #endif  


  // -- Pattern 33 -- Comparison
  #if pattern == 33

	// -- Gaussian filter --
	//   [   , 4 , 6 ,   ,   ]
	//   [   ,16 ,24 ,16 , 4 ]
	//   [ 6 ,24 ,50 ,24 , 6 ]
 	//   [ 4 ,16 ,24 ,16 ,   ]
	//   [   ,   , 6 , 4 ,   ]

    float4 blur_ori = myTex2D(s0, tex + float2(-px,py) * 0.5 * offset_bias); // North West
    blur_ori += myTex2D(s0, tex + float2(px,-py) * 0.5 * offset_bias);  // South East
    blur_ori += myTex2D(s0, tex + float2(px,py) * 0.5 * offset_bias); // North East
  	blur_ori += myTex2D(s0, tex + float2(-px,-py) * 0.5 * offset_bias); // South West

    blur_ori /= 4;  //Divide by the number of texture fetches 

    float4 blur_ori2 = myTex2D(s0, tex + (float2(-px,py) / 3) * offset_bias); // North West
    blur_ori2 += myTex2D(s0, tex + (float2(px,-py) / 3) * offset_bias);  // South East

    blur_ori2 /= 2;


    float4 sharp = ori - blur_ori;  
   
    float sharp_luma = dot(sharp, sharp_strength_luma);
       
    float4 sharp2 = ori - blur_ori2;  
    float sharp_luma2 = dot(sharp2, sharp_strength_luma * 1.5);
    
    sharp_luma -= sharp_luma2;
    
  #endif
  

   /*-----------------------------------------------------------.   
  /                            Sharpen                          /
  '-----------------------------------------------------------*/
  
  // -- Calculate the sharpening --  
  float4 sharp = ori - blur_ori;  //Subtracting the blurred image from the original image
  
  // -- Adjust strength of the sharpening --
  float sharp_luma = dot(sharp, sharp_strength_luma); //Calculate the luma and adjust the strength

  // -- Clamping the maximum amount of sharpening to prevent halo artifacts --
  sharp_luma = clamp(sharp_luma, -sharp_clamp, sharp_clamp);  //TODO Try a curve function instead of a clamp

  // -- Combining the values to get the final sharpened pixel	--
  //float4 done = ori + sharp_luma;    // Add the sharpening to the original.
  float4 done = inputcolor + sharp_luma;    // Add the sharpening to the input color.

  // I have a feeling I might use a lerp somewhere in here to calculate the sharpened pixel slightly faster - will look into it later.

   /*-----------------------------------------------------------.   
  /                     Returning the output                    /
  '-----------------------------------------------------------*/
  #if show_sharpen == 1
    //float3 chroma = ori - luma;
    //done = abs(sharp * 4).rrr;
    done = saturate(0.5 + (sharp_luma * 4)).rrrr;
  #endif

  return done;

}
