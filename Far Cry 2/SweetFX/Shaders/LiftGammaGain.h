   /*-----------------------------------------------------------.   
  /                      Lift Gamma Gain                        /
  '-----------------------------------------------------------*/
/*
  by 3an and CeeJay.dk
  
  
*/

float4 LiftGammaGainPass( float4 colorInput )
{
	float3 color = saturate(colorInput.rgb);
	color = color + (RGB_Lift / 2.0 - 0.5) * (1.0 - color);
	color = saturate(color); 
	colorInput.rgb = pow(RGB_Gain * color, 1.0 / RGB_Gamma);
	return float4(colorInput.rgbb);
}

