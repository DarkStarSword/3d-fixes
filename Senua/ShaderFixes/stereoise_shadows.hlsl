// DarkStarSword's Senua's Sacrifice Lighting Steroisation Shader

#include "stereo_injection_matrices.hlsl"

struct LightingCB {
	float4 unknown[27];
	row_major matrix ScreenToShadowMatrix;
};

cbuffer FViewUniformShaderParameters : register(b13)
{
	struct LightingCB lighting_mono;
}

RWStructuredBuffer<struct LightingCB> lighting_stereo : register(u0);
StructuredBuffer<struct stereo_injection_matrices> stereo_injection : register(t114);

[numthreads(1, 1, 1)]
void main(uint3 tid: SV_DispatchThreadID)
{
	lighting_stereo[0].ScreenToShadowMatrix = mul(stereo_injection[0].screen_inverse, lighting_mono.ScreenToShadowMatrix);
}
