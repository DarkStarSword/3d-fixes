   /*-----------------------------------------------------------.   
  /                          Curves                             /
  '-----------------------------------------------------------*/
/*
  by Christian Cann Schuldt Jensen ~ CeeJay.dk
  
  Curves, uses S-curves to increase contrast, without clipping highlights and shadows.
*/

float4 CurvesPass( float4 colorInput )
{
  float3 color = colorInput.rgb; //original input color
  float3 lumCoeff = float3(0.2126, 0.7152, 0.0722);  //Values to calculate luma with
  float Curves_contrast_blend = Curves_contrast;
  float PI = acos(-1); //3.14159265

  //calculate luma (grey)
  float luma = dot(lumCoeff, color);
	
  //calculate chroma
	float3 chroma = color - luma;
	
	//Apply curve to luma
	
	// -- Curve 1 --
  #if Curves_formula == 1
    luma = sin(PI * 0.5 * luma); // Sin - 721 amd fps
    luma *= luma;  
  #endif
  
  // -- Curve 2 --
  #if Curves_formula == 2
    luma = ( (luma - 0.5) / (0.5 + abs(luma-0.5)) ) + 0.5; // 717 amd fps
  #endif

	// -- Curve 3 --
  #if Curves_formula == 3
    //luma = smoothstep(0.0,1.0,luma); //smoothstep
    luma = luma*luma*(3.0-2.0*luma); //faster smoothstep alternative - 776 amd fps
  #endif

	// -- Curve 4 --
  #if Curves_formula == 4
    luma = 1.1048 / (1.0 + exp(-3.0 * (luma * 2.0 - 1.0))) - (0.1048 / 2.0); //exp formula - 706 amd fps
  #endif

	// -- Curve 5 --
  #if Curves_formula == 5
    luma = 0.5 * (luma + 3.0 * luma * luma - 2.0 * luma * luma * luma); //a simple catmull-rom (0,0,1,1) - 726 amd fps
    Curves_contrast_blend = Curves_contrast * 2.0; //I multiply by two to give it a strength closer to the other curves.
  #endif

 	// -- Curve 6 --
  #if Curves_formula == 6
    luma = luma*luma*luma*(luma*(luma*6.0 - 15.0) + 10.0); //Perlins smootherstep - 752 amd fps
	#endif
	
	// -- Curve 7 --
  #if Curves_formula == 7
    luma = ((luma-0.5) / ((0.5/(4.0/3.0)) + abs((luma-0.5)*1.25))) + 0.5; // amd fps
  #endif
	
  
	//Add back the chroma
	color = luma + chroma;
	
	//Blend by Curves_contrast
	colorInput.rgb = lerp(colorInput.rgb, color, Curves_contrast_blend);
	
  //Return the result
  return colorInput;
}


	//1
	//luma = 0.5 - cos(PI*luma) * 0.5;
	
	//1.2 - same as 1 but a little faster
	//luma = sin(PI * 0.5 * luma); //TODO try merging PI * 0.5 with lumCoeff
	//luma *= luma;
	
	//1.3 - same as 1
	//luma = sin(PI*(luma-0.5)) * 0.5 + 0.5;
	
	//2
	//luma = ( -1.0 + 4.0 * luma + 2.0 * abs(-0.5 + luma) ) / (2.0 + 4.0 * abs(-0.5 + luma) );
	
	//2.2 - same as 2 but slightly faster - I think i prefer the softness of this.
	//luma = ( (luma - 0.5) / (0.5 + abs(luma-0.5) ) ) + 0.5;
	
	//2.3 - same as 2.2 and same speed
	//luma = luma - 0.5;
	//luma = ( luma / (0.5 + abs(luma)) ) + 0.5;
	
	//3 - Smoothstep - Faster than 1 through 2
	//luma = smoothstep(0.0,1.0,luma);
	
	//4 - Alternative to Smoothstep (3) maybe faster
	//luma = luma*luma*(3.0-2.0*luma);
	
	//4.2
	//luma = 3.0 * luma * luma - 2.0 * luma * luma * luma; //1
	
	//4.3
	//float luma_squared = luma * luma;
	//luma = 3.0 * luma_squared - 2.0 * luma_squared * luma; //2

	//4.4
	//float luma_squared = luma * luma;
	//luma = dot( float3(-luma_squared,-luma_squared,-luma_squared) , float3(luma,luma,-3.0) ); //3
	
	//gaussian experiment - needs more work.
	//luma = (1 - (1.0 / sqrt(2.0 * 3.141592 * 0.159155)) * exp(-((luma * luma) / (2.0 * 0.159155))))*1.045;
	
	//5
	//luma = 1.1048 / (1.0 + exp(-3.0 * (luma * 2.0 - 1.0))) - (0.1048 / 2.0);
	
	//6
	//luma = 0.5 * (luma + 3 * luma * luma - 2 * luma * luma * luma);
	
	

/*
//1
0.5 - cos(PI*x) * 0.5
pow(sin((PI * x) / 2.0),2.0)
pow(sin(PI * 0.5 * x),2.0)
sin(PI*(x-0.5)) * 0.5 + 0.5

//2
((x-0.5) / (0.5 + abs(x-0.5))) + 0.5 //5

//3
smoothstep(0.0,1.0,x)

//4
x*x*(3.0-2.0*x)



( -1.0 + 4.0 * x + 2.0 * abs(-0.5 + x) ) / (2.0 + 4.0 * abs(-0.5 + x) ) //4
luma = ( -1.0 + 4.0 * luma + 2.0 * abs(-0.5 + luma) ) / (2.0 + 4.0 * abs(-0.5 + luma) ); //4

(1 - (1.0 / sqrt(2.0 * 3.141592 * 0.159155)) * exp(-((x * x) / (2.0 * 0.159155))))*1.045 //crazy gaussian experiment

1.1048 / (1 + exp(-3 * (x*2-1))) - (0.1048/2)

x*x*x*(x*(x*6 - 15) + 10) //perlins smootherstep

0.5 * (x + 3 * x * x - 2 * x * x * x) //a simple catmull-rom (0,0,1,1)
*/


//TODO : circular s-curve - probably comming in 1.4
/*
static const float sqrt2_05=sqrt(2.f)*0.5f;
static const float smi=1e-4;

#define floatn float

floatn circular_sCurve(floatn x,float 1)
{
	x-=smi;
	
	float st=0;
	floatn p2=step(0.5,x);
	floatn p3=abs(0-p2);
	
	x=fmod(x*2,1);
	x=abs(p3-x);
	
	tau=0
	
	float tau2=tau*tau; 0
	
	float remap0=-1;
	float remap1=0;
	
	x=-x*remap0+tau;
	
	floatn X=1-sqrt(1-x*x);
	X=(X-remap1)/((1-tau)-remap1);
	
	return (abs(p3-saturate(X))+p2)*0.5;		
}
*/