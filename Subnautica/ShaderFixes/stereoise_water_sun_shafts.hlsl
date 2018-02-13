#include "unity_cbuffers.hlsl"

cbuffer UnityPerFrame : register(b11)
{
	struct UnityPerFrame MonoPerFrameFromEarlier;
}
RWStructuredBuffer<struct UnityPerFrame> StereoPerFrame : register(u2);

cbuffer IVP : register(b10)
{
	column_major matrix ivp_from_earlier;
}

// Shader specific globals buffers:
struct WaterSunShafts_VS_Globals
{
};

struct WaterSunShafts_PS_Globals
{
//   Vector 416 [_ImagePlaneSize] 2
//   ScalarInt 512 [_CascadeIndex]
//   Matrix 448 [_CameraToWorldMatrix]
//
//   Vector 64 [_UweFogWsLightDirection] 3
//   Vector 80 [_UweFogLightColor]
//   Vector 128 [_UweVsWaterPlane]
//   Float 272 [_UweVolumeTextureSlices]
//   Float 276 [_UweExtinctionAndScatteringScale]
//   Float 280 [_UweSunAttenuationFactor]
//   Vector 304 [_UweColorCastFactor] 2
//   Vector 336 [_UweCausticsAmount] 3
//   Float 424 [_StartDistance]
//   Float 428 [_MaxDistance]
//   Float 432 [_ShaftsScale]
//   Float 436 [_Intensity]
//   Matrix 144 [_UweCameraToVolumeMatrix]
//   Matrix 352 [_CameraToCausticsMatrix]
	float4 pad1[9];
	row_major matrix _UweCameraToVolumeMatrix;

	float4 pad2[9];
	row_major matrix _CameraToCausticsMatrix;

	float4 pad3[2];
	row_major matrix _CameraToWorldMatrix;
};

cbuffer WaterSunShafts_PS_Globals : register(b13)
{
	struct WaterSunShafts_PS_Globals MonoGlobals;
}

RWStructuredBuffer<struct WaterSunShafts_PS_Globals> StereoGlobals : register(u0);

#include "matrix.hlsl"

Texture1D<float4> IniParams : register(t120);
Texture2D<float4> StereoParams : register(t125);

[numthreads(1, 1, 1)]
void main(uint3 tid: SV_DispatchThreadID)
{
	float4 s = StereoParams.Load(0);
	float sep = s.x, conv = s.y;

	// NOTE: We cannot use the VP matrix from this draw call, as it is a
	// full screen matrix in the form:
	//      2  0  0    0
	//      0 -2  0    0
	//      0  0 ~0.01 0
	//     -1  1 ~1    1
	// So, this one we use was obtained sometime earlier in the frame and
	// hopefully is valid:
	matrix vp = MonoPerFrameFromEarlier.unity_MatrixVP;

	matrix inv_v = MonoGlobals._CameraToWorldMatrix;
	matrix p = mul(inv_v, vp);

#if 0 /* Use cleaned projection matrix - only minor difference in this case */
	// XXX: For some reason, using Resource_Inverse_VP_CB isn't working
	//matrix inv_vp = ivp_from_earlier;
	matrix inv_vp = inverse(vp);

	// Flipped projection, so z=0 is far, z=1 is near
	float4 tmp = mul(float4(0, 0, 0, 1), inv_vp);
	float far = mul(tmp / tmp.w, vp).w;
	tmp = mul(float4(0, 0, 1, 1), inv_vp);
	float near = mul(tmp / tmp.w, vp).w;

	// Then we make our own cleaned up projection matrix, matching Unity's
	// flipped projection with our stereo correction inserted.
	float w = p._m00;
	float h = p._m11;
	// Flipped projection, so near instead of far:
	float a = near / (far - near);
	float b = (near * far) / (far - near);
	float c = -1; // Flipped projection
	matrix cleaned_projection = matrix(
		w, 0, 0, 0,
		0, h, 0, 0,
		0, 0, a, c,
		0, 0, b, 0
	);

	matrix stereo_projection = cleaned_projection;
#else
	matrix stereo_projection = p;
#endif

	stereo_projection._m20 = -sep; // EXPLAIN ME: Why negative when UE4 is positive? Flipped projection?
	stereo_projection._m30 = -sep * conv;

#if 0
	matrix view_injection_f = mul(stereo_projection, inverse(p));
	matrix view_injection_i = inverse(view_injection_f);
#else
	// Works out the same, but one inverse instead of two:
	matrix view_injection_i = mul(p, inverse(stereo_projection));
#endif

	// Very important:
	StereoGlobals[0]._CameraToCausticsMatrix = mul(view_injection_i,  MonoGlobals._CameraToCausticsMatrix);
	// Less obvious, but still required for correct shaft placement:
	StereoGlobals[0]._CameraToWorldMatrix = mul(view_injection_i, MonoGlobals._CameraToWorldMatrix);

	// No visible difference that I can see:
	StereoGlobals[0]._UweCameraToVolumeMatrix = mul(view_injection_i, MonoGlobals._UweCameraToVolumeMatrix);
}
