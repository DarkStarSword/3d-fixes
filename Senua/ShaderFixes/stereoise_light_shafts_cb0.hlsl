// DarkStarSword's Senua's Sacrifice Light Shaft Steroisation Shader

#define NEW_UE4
#define SENUA

#include "UE4FViewUniformShaderParameters.hlsl"

// Clearly not a stock UE4 effect - most of these are readily available in
// FViewUniformShaderParameters, so they could have just used that directly.
// Used Frame Analysis to match these up.

struct LightShaftsCB0 {
	/*  4 ->  0 */ FMatrix WorldToClip;
	/* 44 ->  4 */ FMatrix ScreenToTranslatedWorld;
	/*  8 ->  8 */ FMatrix TranslatedWorldToView;
	/* 56 -> 12 */ FVector WorldCameraOrigin;
	float UAV_PADDING_WorldCameraOrigin; // Has the value 10
	// There's another parameter after that, which is probably specific to the effect
};

RWStructuredBuffer<struct LightShaftsCB0> light_shafts_cb0 : register(u0);
StructuredBuffer<struct FViewUniformShaderParameters> stereo : register(t113);

[numthreads(1, 1, 1)]
void main(uint3 tid: SV_DispatchThreadID)
{
	light_shafts_cb0[0].WorldToClip = stereo[0].WorldToClip;
	light_shafts_cb0[0].ScreenToTranslatedWorld = stereo[0].ScreenToTranslatedWorld;
	light_shafts_cb0[0].TranslatedWorldToView = stereo[0].TranslatedWorldToView;
	light_shafts_cb0[0].WorldCameraOrigin = stereo[0].WorldCameraOrigin;
}
