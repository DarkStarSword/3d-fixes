/*
DPX/Cineon shader by Loadus ( http://www.loadusfx.net/virtualdub/DPX.fx )
Ported to SweetFX by CeeJay.dk

Version 1.0
*/

static float3x3 RGB =
{
2.67147117265996,-1.26723605786241,-0.410995602172227,
-1.02510702934664,1.98409116241089,0.0439502493584124,
0.0610009456429445,-0.223670750812863,1.15902104167061
};

static float3x3 XYZ =
{
0.500303383543316,0.338097573222739,0.164589779545857,
0.257968894274758,0.676195259144706,0.0658358459823868,
0.0234517888692628,0.1126992737203,0.866839673124201
};

float4 DPXPass(float4 InputColor) : COLOR0 {

	float DPXContrast = 0.1;

	float DPXGamma = 1.0;

	float RedCurve = Red;
	float GreenCurve = Green;
	float BlueCurve = Blue;

	float3 B = InputColor.rgb;
	//float3 Bn = B; // I used InputColor.rgb instead.

	B = pow(B, 1.0/DPXGamma);

	B.r = pow(B.r, 1.00);
	B.g = pow(B.g, 1.00);
	B.b = pow(B.b, 1.00);

        B = (B * (1.0 - DPXContrast)) + DPXContrast / 2.0;
 	
 	B.r = (1.0 /(1.0 + exp(- RedCurve * (B.r - RedC))) - (1.0 / (1.0 + exp(RedCurve / 2.0))))/(1.0 - 2.0 * (1.0 / (1.0 + exp(RedCurve / 2.0))));				
	B.g = (1.0 /(1.0 + exp(- GreenCurve * (B.g - GreenC))) - (1.0 / (1.0 + exp(GreenCurve / 2.0))))/(1.0 - 2.0 * (1.0 / (1.0 + exp(GreenCurve / 2.0))));				
	B.b = (1.0 /(1.0 + exp(- BlueCurve * (B.b - BlueC))) - (1.0 / (1.0 + exp(BlueCurve / 2.0))))/(1.0 - 2.0 * (1.0 / (1.0 + exp(BlueCurve / 2.0))));					

        //TODO use faster code for conversion between RGB/HSV  -  see http://www.chilliant.com/rgb2hsv.html
	   float value = max(max(B.r, B.g), B.b);
	   float3 color = B / value;
	
	   color = pow(color, 1.0/ColorGamma);
	
	   float3 c0 = color * value;

	   c0 = mul(XYZ, c0);

	   float luma = dot(c0, float3(0.30, 0.59, 0.11)); //Use BT 709 instead?
	   float3 chroma = c0 - luma;

	   c0 = luma + chroma * DPXSaturation;
	   c0 = mul(RGB, c0);
	
	InputColor.rgb = lerp(InputColor.rgb, c0, Blend); //as long as Blend is always 0 we don't really need to lerp. The compiler *should* be smart enough to optimize this though (check to be sure)

	return InputColor;
}