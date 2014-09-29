   /*-----------------------------------------------------------.   
  /                          Vibrance                           /
  '-----------------------------------------------------------*/
/*
  by Christian Cann Schuldt Jensen ~ CeeJay.dk
  
  Vibrance intelligently boosts the saturation of pixels
  so pixels that had little color get a larger boost than pixels that had a lot.
  
  This avoids oversaturation of pixels that were already very saturated.
*/

float4 VibrancePass( float4 colorInput )
{
	float4 color = colorInput; //original input color
    float3 lumCoeff = float3(0.2126, 0.7152, 0.0722);  //Values to calculate luma with

	float luma = dot(lumCoeff, color.rgb); //calculate luma (grey)
	
	float max_color = max(colorInput.r, max(colorInput.g,colorInput.b)); //Find the strongest color
	float min_color = min(colorInput.r, min(colorInput.g,colorInput.b)); //Find the weakest color
	
    float color_saturation = max_color - min_color; //The difference between the two is the saturation

    //color.rgb = lerp(luma, color.rgb, (1.0 + (Vibrance * (1.0 - color_saturation)))); //extrapolate between luma and original by 1 + (1-saturation) - simple
  
    color.rgb = lerp(luma, color.rgb, (1.0 + (Vibrance * (1.0 - (sign(Vibrance) * color_saturation))))); //extrapolate between luma and original by 1 + (1-saturation) - current
  
    //color.rgb = lerp(luma, color.rgb, 1.0 + (1.0-pow(color_saturation, 1.0 - (1.0-Vibrance))) ); //pow version
  
	return color; //return the result
	//return color_saturation.xxxx; //Visualize the saturation
}

