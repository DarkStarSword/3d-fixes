   /*-----------------------------------------------------------.   
  /                           Dither                            /
  '-----------------------------------------------------------*/
/* 
  Dither version 1.0.11
  by Christian Cann Schuldt Jensen ~ CeeJay.dk
  
  Does dithering of the greather than 8-bit per channel precision used in shaders.
  Even halfs offer 10(+1)bit per channel
*/

float XOR( float xor_A, float xor_B )
{
  return saturate( dot(float4(-xor_A ,-xor_A ,xor_A , xor_B) , float4(xor_B, xor_B ,1.0 ,1.0 ) ) ); // (-A * B) + (-A * B) + (A * 1.0) + (B * 1.0)
}

float4 DitherPass( float4 colorInput, float2 tex )
{

   float4 color = colorInput;
   //color = tex.x / 2.0; //draw a gradient for testing.
   
   float dither_size = 2.0;  //move to settings?
   float dither_bit  = 8.0;  //move to settings?
   
   /*
   //method 1 (works but not that fast)
   float pixel_position = dot(tex,screen_size);
   float grid_position = round(pixel_position) % dither_size;
   */

   /*
   //method 2 (faster)
   float pixel_position = dot(tex,(screen_size / dither_size));
   float grid_position = abs(round(pixel_position) - pixel_position); 
   */
   
   /*
   //method 3 (fastest) - Works fine on Nvidia - errors on AMD.
   float pixel_position = dot(tex,(screen_size / dither_size));
   float grid_position = abs(ceil(pixel_position) - pixel_position);
   //float grid_position = abs((ceil(pixel_position) - pixel_position)* 2.0);
   */
   
   /*
   //method 4 (doesn't work right - precision errors)
   float pixel_position = dot(tex,(screen_size / dither_size));
   float grid_position = abs(frac(pixel_position));      
   */
   
   
   /*
   //method 5 - XOR (might come in handy later)
   //float pixel_position = dot(tex,(screen_size / dither_size));
   float grid_position = ceil(XOR(tex.x+0.7075,tex.y+0.7075));
   */
   
   /*
   //method 6 (Works on nvidia and is just as fast as method 3)
   float pixel_position = dot(tex,(screen_size / dither_size))-0.1;
   float grid_position = abs(floor(pixel_position) - pixel_position);
   */
   
   /*
   //method 7 (Works on nvidia and is just as fast as method 3)
   float pixel_position = dot(tex,(screen_size / dither_size))+0.25;
   float grid_position = abs(floor(pixel_position) - pixel_position);
   */
   
   /*
   //method 8 (ceil version of 7) - returns 0.25 and 0.75
   float pixel_position = dot(tex,(screen_size / dither_size))+0.25;
   float grid_position = abs(ceil(pixel_position) - pixel_position);
   */
   
   /*
   //method 9 (frac version of 7) - Works on nvidia and is even faster than method 3!
   float pixel_position = dot(tex,(screen_size / dither_size))+0.25;
   float grid_position = frac(pixel_position); //returns 0.25 and 0.75
   */
   
   
   //method 10 (a more elegant one-line version of 9)
   //float grid_position = frac(dot(tex,(screen_size / dither_size))+0.25); //returns 0.25 and 0.75
  
   //method 11 (a more elegant one-line version of 9)
   float grid_position = frac(dot(tex,(screen_size / dither_size)) + (0.5 / dither_size)); //returns 0.25 and 0.75
  
   //Calculate how big the shift should be
   float dither_shift = (0.25) * (1.0 / (pow(2,dither_bit) - 1.0)); // 0.25 seems good both when using math and when eyeballing it. So does 0.75 btw.

   //shift the color by dither_shift    
   color.rgb += lerp(2.0 * dither_shift,(-2.0 * dither_shift),grid_position); 
   //color += lerp(dither_shift,(-dither_shift),grid_position);

   return color;
   //return grid_position.xxxx; //visualize grid for debugging purposes
}