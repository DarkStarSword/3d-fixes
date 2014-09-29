   /*-----------------------------------------------------------.   
  /                          Vignette                           /
  '-----------------------------------------------------------*/
/*
  Version 1.1
  
  Darkens the edges of the image to make it look more like it was shot with a camera lens.
  May cause banding artifacts.
*/

float4 VignettePass( float4 colorInput, float2 tex )
{
	float4 vignette = colorInput;
	
	//Set the center
	float2 tc = tex - VignetteCenter;
	
	//Make the ratio 1:1
	tc.x *= (SMAA_PIXEL_SIZE.y / SMAA_PIXEL_SIZE.x);
	
	//Calculate the distance
    float v = length(tc) / VignetteRadius;
    
    //Apply the vignette
	vignette.rgb = vignette.rgb * (1.0 + pow(v, VignetteSlope) * VignetteAmount); //pow - multiply
	
	return vignette;
}
