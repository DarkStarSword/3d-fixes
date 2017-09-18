// DarkStarSword's Senua's Sacrifice Light Shaft Steroisation Shader

#include "UE4FViewUniformShaderParameters.hlsl"

// Clearly not a stock UE4 effect - most of these are readily available in
// FViewUniformShaderParameters, so they could have just used that directly.
// Used Frame Analysis to match these up.

struct LightShaftsCB1 {
	/*   4 ->  0 */ FMatrix WorldToClip;
	/*  44 ->  4 */ FMatrix ScreenToTranslatedWorld;
	/*   8 ->  8 */ FMatrix TranslatedWorldToView;
	/*  56 -> 12 */ FVector WorldCameraOrigin;
	float UAV_PADDING_WorldCameraOrigin; // Has the value 10
	/*  64 -> 13 */ FMatrix PrevViewProj;
	/* 107 -> 17 */ FMatrix PrevScreenToTranslatedWorld;
	/*  85 -> 21 */ FMatrix PrevTranslatedWorldToView;
	/* 100 -> 25 */ FVector PrevWorldCameraOrigin;
	float UAV_PADDING_PrevWorldCameraOrigin; // Has the value 10
	// Effect specific effects follow
};

RWStructuredBuffer<struct LightShaftsCB1> light_shafts_cb1 : register(u0);
StructuredBuffer<struct FViewUniformShaderParameters> stereo : register(t113);

[numthreads(1, 1, 1)]
void main(uint3 tid: SV_DispatchThreadID)
{
	light_shafts_cb1[0].WorldToClip = stereo[0].WorldToClip;
	light_shafts_cb1[0].ScreenToTranslatedWorld = stereo[0].ScreenToTranslatedWorld;
	// light_shafts_cb1[0].TranslatedWorldToView = stereo[0].TranslatedWorldToView;
	light_shafts_cb1[0].WorldCameraOrigin = stereo[0].WorldCameraOrigin;
	light_shafts_cb1[0].PrevViewProj = stereo[0].PrevViewProj;
	light_shafts_cb1[0].PrevScreenToTranslatedWorld = stereo[0].PrevScreenToTranslatedWorld;
	// light_shafts_cb1[0].PrevTranslatedWorldToView = stereo[0].PrevTranslatedWorldToView;
	light_shafts_cb1[0].PrevWorldCameraOrigin = stereo[0].PrevWorldCameraOrigin;
}
