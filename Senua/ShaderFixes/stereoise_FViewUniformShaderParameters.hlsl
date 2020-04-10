// DarkStarSword's UE4 FViewUniformShaderParameters steroisation shader

// If this is defined the shader will copy the previous frame translations from
// a copy of the previous frame's UAV in t113. If it is not defined the shader
// will calculate them from scratch. Not sure which will perform better.
#undef COPY_PREV_FRAME

#include "UE4FViewUniformShaderParameters.hlsl"

struct StereoInjectionMatrices {
	row_major matrix sv_position_inv;
};

cbuffer FViewUniformShaderParameters : register(b13)
{
	struct FViewUniformShaderParameters mono;
}

RWStructuredBuffer<struct FViewUniformShaderParameters> stereo : register(u0);
RWStructuredBuffer<struct StereoInjectionMatrices> injection : register(u1);
StructuredBuffer<struct FViewUniformShaderParameters> prev : register(t113);

matrix inverse(matrix m)
{
	matrix inv;

	float det = determinant(m);
	inv[0].x = m[1].y*(m[2].z*m[3].w - m[2].w*m[3].z) + m[1].z*(m[2].w*m[3].y - m[2].y*m[3].w) + m[1].w*(m[2].y*m[3].z - m[2].z*m[3].y);
	inv[0].y = m[0].y*(m[2].w*m[3].z - m[2].z*m[3].w) + m[0].z*(m[2].y*m[3].w - m[2].w*m[3].y) + m[0].w*(m[2].z*m[3].y - m[2].y*m[3].z);
	inv[0].z = m[0].y*(m[1].z*m[3].w - m[1].w*m[3].z) + m[0].z*(m[1].w*m[3].y - m[1].y*m[3].w) + m[0].w*(m[1].y*m[3].z - m[1].z*m[3].y);
	inv[0].w = m[0].y*(m[1].w*m[2].z - m[1].z*m[2].w) + m[0].z*(m[1].y*m[2].w - m[1].w*m[2].y) + m[0].w*(m[1].z*m[2].y - m[1].y*m[2].z);
	inv[1].x = m[1].x*(m[2].w*m[3].z - m[2].z*m[3].w) + m[1].z*(m[2].x*m[3].w - m[2].w*m[3].x) + m[1].w*(m[2].z*m[3].x - m[2].x*m[3].z);
	inv[1].y = m[0].x*(m[2].z*m[3].w - m[2].w*m[3].z) + m[0].z*(m[2].w*m[3].x - m[2].x*m[3].w) + m[0].w*(m[2].x*m[3].z - m[2].z*m[3].x);
	inv[1].z = m[0].x*(m[1].w*m[3].z - m[1].z*m[3].w) + m[0].z*(m[1].x*m[3].w - m[1].w*m[3].x) + m[0].w*(m[1].z*m[3].x - m[1].x*m[3].z);
	inv[1].w = m[0].x*(m[1].z*m[2].w - m[1].w*m[2].z) + m[0].z*(m[1].w*m[2].x - m[1].x*m[2].w) + m[0].w*(m[1].x*m[2].z - m[1].z*m[2].x);
	inv[2].x = m[1].x*(m[2].y*m[3].w - m[2].w*m[3].y) + m[1].y*(m[2].w*m[3].x - m[2].x*m[3].w) + m[1].w*(m[2].x*m[3].y - m[2].y*m[3].x);
	inv[2].y = m[0].x*(m[2].w*m[3].y - m[2].y*m[3].w) + m[0].y*(m[2].x*m[3].w - m[2].w*m[3].x) + m[0].w*(m[2].y*m[3].x - m[2].x*m[3].y);
	inv[2].z = m[0].x*(m[1].y*m[3].w - m[1].w*m[3].y) + m[0].y*(m[1].w*m[3].x - m[1].x*m[3].w) + m[0].w*(m[1].x*m[3].y - m[1].y*m[3].x);
	inv[2].w = m[0].x*(m[1].w*m[2].y - m[1].y*m[2].w) + m[0].y*(m[1].x*m[2].w - m[1].w*m[2].x) + m[0].w*(m[1].y*m[2].x - m[1].x*m[2].y);
	inv[3].x = m[1].x*(m[2].z*m[3].y - m[2].y*m[3].z) + m[1].y*(m[2].x*m[3].z - m[2].z*m[3].x) + m[1].z*(m[2].y*m[3].x - m[2].x*m[3].y);
	inv[3].y = m[0].x*(m[2].y*m[3].z - m[2].z*m[3].y) + m[0].y*(m[2].z*m[3].x - m[2].x*m[3].z) + m[0].z*(m[2].x*m[3].y - m[2].y*m[3].x);
	inv[3].z = m[0].x*(m[1].z*m[3].y - m[1].y*m[3].z) + m[0].y*(m[1].x*m[3].z - m[1].z*m[3].x) + m[0].z*(m[1].y*m[3].x - m[1].x*m[3].y);
	inv[3].w = m[0].x*(m[1].y*m[2].z - m[1].z*m[2].y) + m[0].y*(m[1].z*m[2].x - m[1].x*m[2].z) + m[0].z*(m[1].x*m[2].y - m[1].y*m[2].x);
	inv /= det;

	return inv;
}

Texture1D<float4> IniParams : register(t120);
Texture2D<float4> StereoParams : register(t125);

void update_prev_frame_transformations_common(matrix prev_stereo_projection, matrix cur_stereo_injection_f, matrix cur_stereo_injection_i)
{
	matrix view_no_translate = mono.PrevTranslatedWorldToView;
	view_no_translate._m30_m31_m32 = 0;

	stereo[0].PrevViewRotationProj = mul(view_no_translate, prev_stereo_projection);

	// Fixes temporal AA motion blur, but seems to cause a slight judder:
	//stereo[0].ClipToPrevClip = mul(mul(cur_stereo_injection_i, mono.ClipToPrevClip), stereo_injection_f);
	// No judder, and still looks fine despite this hack:
	stereo[0].ClipToPrevClip = mul(mul(cur_stereo_injection_i, mono.ClipToPrevClip), cur_stereo_injection_f);
}

#ifdef COPY_PREV_FRAME
void update_prev_frame_transformations(float sep, float conv, matrix cur_stereo_injection_f, matrix cur_stereo_injection_i)
{
	matrix stereo_projection = mono.PrevViewToClip;
	stereo_projection._m20 = sep;
	stereo_projection._m30 = -sep * conv;
	matrix stereo_injection_f = mul(mono.PrevClipToView, stereo_projection);

	stereo[0].PrevProjection = prev[0].ViewToClip;
	stereo[0].PrevViewProj = prev[0].WorldToClip;
	stereo[0].PrevViewToClip = prev[0].ViewToClip;
	stereo[0].PrevClipToView = prev[0].ClipToView;
	stereo[0].PrevTranslatedWorldToClip = prev[0].TranslatedWorldToClip;
	stereo[0].PrevTranslatedWorldToView = prev[0].TranslatedWorldToView;
	stereo[0].PrevViewToTranslatedWorld = prev[0].ViewToTranslatedWorld;
	stereo[0].PrevTranslatedWorldToCameraView = prev[0].TranslatedWorldToCameraView;
	stereo[0].PrevCameraViewToTranslatedWorld = prev[0].CameraViewToTranslatedWorld;
	stereo[0].PrevWorldCameraOrigin = prev[0].WorldCameraOrigin;
	stereo[0].PrevWorldViewOrigin = prev[0].WorldViewOrigin;
	stereo[0].PrevPreViewTranslation = prev[0].PreViewTranslation;
	// TODO: Could calculate ClipToWorld like the other version, but I'd
	// rather not inverse if I don't have to, and this doesn't seem to
	// affect anything obvious:
	// TODO stereo[0].PrevInvViewProj = ClipToWorld;
	stereo[0].PrevScreenToTranslatedWorld = prev[0].ScreenToTranslatedWorld;
#ifdef SENUA
	stereo[0].senua_specific_111 = prev[0].WorldToClip;
#endif

	update_prev_frame_transformations_common(stereo_projection, cur_stereo_injection_f, cur_stereo_injection_i);
}

#else /* COPY_PREV_FRAME */

void update_prev_frame_transformations(float sep, float conv, matrix cur_stereo_injection_f, matrix cur_stereo_injection_i)
{
	matrix stereo_projection = mono.PrevViewToClip;
	stereo_projection._m20 = sep;
	stereo_projection._m30 = -sep * conv;
	matrix stereo_injection_f = mul(mono.PrevClipToView, stereo_projection);
	matrix stereo_injection_i = inverse(stereo_injection_f);

	float4 cam_adj_clip = float4(-sep * conv, 0, 0, 0);
	float3 cam_adj_view = mul(cam_adj_clip, mono.PrevClipToView).xyz;
	float3 cam_adj_world = mul(cam_adj_view, mono.PrevViewToTranslatedWorld).xyz;

	stereo[0].PrevProjection = stereo_projection;
	matrix stereo_WorldToClip = mul(mono.PrevViewProj, stereo_injection_f);
	stereo[0].PrevViewProj = stereo_WorldToClip;
	stereo[0].PrevViewToClip = stereo_projection;
	stereo[0].PrevClipToView = mul(stereo_injection_i, mono.PrevClipToView);
	stereo[0].PrevTranslatedWorldToClip = mul(mono.PrevTranslatedWorldToClip, stereo_injection_f);
	//stereo[0].PrevTranslatedWorldToView = prev[0].TranslatedWorldToView;
	//stereo[0].PrevViewToTranslatedWorld = prev[0].ViewToTranslatedWorld;
	//stereo[0].PrevTranslatedWorldToCameraView = prev[0].TranslatedWorldToCameraView;
	//stereo[0].PrevCameraViewToTranslatedWorld = prev[0].CameraViewToTranslatedWorld;
	stereo[0].PrevWorldCameraOrigin = mono.PrevWorldCameraOrigin - cam_adj_world;
	stereo[0].PrevWorldViewOrigin = mono.PrevWorldViewOrigin - cam_adj_world;
	//stereo[0].PrevPreViewTranslation = prev[0].PreViewTranslation;
	stereo[0].PrevInvViewProj = inverse(stereo_WorldToClip);
	stereo[0].PrevScreenToTranslatedWorld = prev[0].ScreenToTranslatedWorld;
#ifdef SENUA
	stereo[0].senua_specific_111 = prev[0].WorldToClip;
#endif

	update_prev_frame_transformations_common(stereo_projection, cur_stereo_injection_f, cur_stereo_injection_i);
}
#endif /* COPY_PREV_FRAME */

[numthreads(1, 1, 1)]
void main(uint3 tid: SV_DispatchThreadID)
{
	int i;

	float4 s = StereoParams.Load(0);
	float sep = s.x, conv = s.y;

	// What we are essentially trying to do is remove the inverse
	// projection matrix and replace it with a modified version that has a
	// stereo correction embedded, but in a manner that works regardless of
	// the matrix we are modifying is a pure inverse projection matrix
	// (which we could do much simpler than this), or a composite inverse
	// VP or inverse MVP matrix.
	//
	// Mathematically we can remove an inverse projection matrix from the
	// start of an arbitrary composite by multiplying by its forwards, then
	// we can multiply by the new stereo corrected projection matrix
	// (called 1/SP): 1/SP * P * 1/P * 1/V * 1/M
	//
	// But matrix maths allows us to do the 1/SP * P multiplication first,
	// so if we can find that matrix then we would have a single matrix
	// that we can multiply any inverse MVP, inverse VP or inverse P matrix
	// by to inject a stereo correction.

	// For UE4 we are deriving the stereo injection matrix from first
	// principles. We start by creating a pair of projection matrices with
	// built in stereo corrections:
	matrix stereo_projection = mono.ViewToClip;
	stereo_projection._m20 = sep;
	stereo_projection._m30 = -sep * conv;

	float4 cam_adj_clip = float4(-sep * conv, 0, 0, 0);
	float3 cam_adj_world = mul(cam_adj_clip, mono.ClipToTranslatedWorld).xyz;

	// Calculate the forwards stereo injection matrices, by multiplying the
	// inverse projection matrix by the forwards stereo projection matrix:
	matrix stereo_injection_f = mul(mono.ClipToView, stereo_projection);
	// Get the inverse stereo injection matrices:
	matrix stereo_injection_i = inverse(stereo_injection_f);

	// Use the stereo injection matrices to add a stereo corrections to
	// various matrices (not all of these are tested):
	stereo[0].TranslatedWorldToClip = mul(mono.TranslatedWorldToClip, stereo_injection_f);
	matrix stereo_WorldToClip = mul(mono.WorldToClip, stereo_injection_f);
	stereo[0].WorldToClip = stereo_WorldToClip;
	//stereo[0].TranslatedWorldToView = mono.TranslatedWorldToView;
	//stereo[0].ViewToTranslatedWorld = mono.ViewToTranslatedWorld;
	//stereo[0].TranslatedWorldToCameraView = mono.TranslatedWorldToCameraView;
	//stereo[0].CameraViewToTranslatedWorld = mono.CameraViewToTranslatedWorld;
	stereo[0].ViewToClip = stereo_projection;
	stereo[0].ClipToView = mul(stereo_injection_i, mono.ClipToView);
	matrix stereo_ClipToTranslatedWorld = mul(stereo_injection_i, mono.ClipToTranslatedWorld);
	stereo[0].ClipToTranslatedWorld = stereo_ClipToTranslatedWorld;

	// We actually need to alter SVPositionToTranslatedWorld, but that
	// matrix does not begin with an inverse projection matrix - it has an
	// additional matrix that does a resolution divide and viewspace
	// offset. We can derive that matrix easily enough (alternatively, we
	// could generate it based on the resolution and viewport, but we'd
	// need to be certain that we are always using the same values as the
	// game):
	matrix SVPositionToClip = mul(mono.SVPositionToTranslatedWorld, mono.TranslatedWorldToClip);
	matrix stereo_SVPositionToTranslatedWorld = mul(SVPositionToClip, stereo_ClipToTranslatedWorld);
	stereo[0].SVPositionToTranslatedWorld = stereo_SVPositionToTranslatedWorld;

	// Calculate SVPosition inverse steroisation matrix for SVPositionToDecal:
	injection[0].sv_position_inv = mul(stereo_SVPositionToTranslatedWorld, inverse(mono.SVPositionToTranslatedWorld));

	matrix ScreenToClip = mul(mono.ScreenToWorld, mono.WorldToClip);
	// Should be able to do better than inversing another matrix - we can
	// multiply the stereo_ClipToTranslatedWorld by a translation matrix:
	matrix stereo_ClipToWorld = inverse(stereo_WorldToClip);
	stereo[0].ScreenToWorld = mul(ScreenToClip, stereo_ClipToWorld);
	stereo[0].ScreenToTranslatedWorld = mul(ScreenToClip, stereo_ClipToTranslatedWorld);

	// WorldCameraOrigin and WorldViewOrigin appear to be the same thing - is there a difference?
	stereo[0].WorldCameraOrigin = mono.WorldCameraOrigin - cam_adj_world;
	stereo[0].TranslatedWorldCameraOrigin = mono.TranslatedWorldCameraOrigin - cam_adj_world; // Fixes reflections
	stereo[0].WorldViewOrigin = mono.WorldViewOrigin - cam_adj_world;
	//stereo[0].PreViewTranslation - do not adjust

	update_prev_frame_transformations(sep, conv, stereo_injection_f, stereo_injection_i);
}
