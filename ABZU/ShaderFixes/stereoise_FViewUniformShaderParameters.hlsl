// UnrealEngine/Engine/Source/Runtime/Engine/Public/SceneView.h
// UnrealEngine/Engine/Source/Runtime/Engine/Private/SceneView.cpp
cbuffer FViewUniformShaderParameters : register(b1)
{
	/*   0 */ row_major matrix TranslatedWorldToClip;
	/*   4 */ row_major matrix WorldToClip;
	/*   8 */ row_major matrix TranslatedWorldToView;
	/*  12 */ row_major matrix ViewToTranslatedWorld;
	/*  16 */ row_major matrix TranslatedWorldToCameraView;
	/*  20 */ row_major matrix CameraViewToTranslatedWorld;
	/*  24 */ row_major matrix ViewToClip;
	/*  28 */ row_major matrix ClipToView;
	/*  32 */ row_major matrix ClipToTranslatedWorld;
	/*  36 */ row_major matrix SVPositionToTranslatedWorld; // Variant of ClipToTranslatedWorld that includes a resolution divide
	/*  40 */ row_major matrix ScreenToWorld;
	/*  44 */ row_major matrix ScreenToTranslatedWorld;

	/*  48 */ float4 ViewForward;
	/*  49 */ float4 ViewUp;
	/*  50 */ float4 ViewRight;
	// Newer versions of UE4 also include:
	// float4 HMDViewNoRollUp;
	// float4 HMDViewNoRollRight;
	/*  51 */ float4 InvDeviceZToWorldZTransform;
	/*  52 */ float4 ScreenPositionScaleBias;
	/*  53 */ float4 WorldCameraOrigin;
	/*  54 */ float4 TranslatedWorldCameraOrigin;
	/*  55 */ float4 WorldViewOrigin;
	/*  56 */ float4 PreViewTranslation;

	/*  57 */ row_major matrix PrevProjection;
	/*  61 */ row_major matrix PrevViewProj;
	/*  65 */ row_major matrix PrevViewRotationProj;
	/*  69 */ row_major matrix PrevViewToClip;
	/*  73 */ row_major matrix PrevClipToView;
	/*  77 */ row_major matrix PrevTranslatedWorldToClip;
	/*  81 */ row_major matrix PrevTranslatedWorldToView;
	/*  85 */ row_major matrix PrevViewToTranslatedWorld;
	/*  89 */ row_major matrix PrevTranslatedWorldToCameraView;
	/*  93 */ row_major matrix PrevCameraViewToTranslatedWorld;

	/*  97 */ float4 PrevWorldCameraOrigin;
	/*  98 */ float4 PrevWorldViewOrigin;
	/*  99 */ float4 PrevPreViewTranslation;

	/* 100 */ matrix PrevInvViewProj;
	/* 104 */ matrix PrevScreenToTranslatedWorld;
	/* 108 */ matrix ClipToPrevClip;

	// Newer UE4 versions have more fields after this point
}

RWBuffer<float4> modified_SVPositionToTranslatedWorld : register(u0);

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

matrix inverse(float4 m0, float4 m1, float4 m2, float4 m3)
{
	return inverse(matrix(m0, m1, m2, m3));
}

#define MATRIX(cb, idx) matrix(cb[idx], cb[idx+1], cb[idx+2], cb[idx+3])

Texture1D<float4> IniParams : register(t120);
Texture2D<float4> StereoParams : register(t125);

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
	matrix stereo_projection_l = ViewToClip;
	matrix stereo_projection_r = ViewToClip;
	stereo_projection_l._m20 = -sep;
	stereo_projection_l._m30 = sep * conv;
	stereo_projection_r._m20 = sep;
	stereo_projection_r._m30 = -sep * conv;

	// Calculate the forwards stereo injection matrices, by multiplying the
	// inverse projection matrix by the forwards stereo projection matrix:
	matrix stereo_injection_f_l = mul(ClipToView, stereo_projection_l);
	matrix stereo_injection_f_r = mul(ClipToView, stereo_projection_r);
	// Get the inverse stereo injection matrices:
	matrix stereo_injection_i_l = inverse(stereo_injection_f_l);
	matrix stereo_injection_i_r = inverse(stereo_injection_f_r);

	// Use the stereo injection matrices to add a stereo correction to
	// ClipToTranslatedWorld:
	matrix l = mul(stereo_injection_i_l, ClipToTranslatedWorld);
	matrix r = mul(stereo_injection_i_r, ClipToTranslatedWorld);

	// We actually need to alter SVPositionToTranslatedWorld, but that
	// matrix does not begin with an inverse projection matrix - it has an
	// additional matrix that does a resolution divide and viewspace
	// offset. We can derive that matrix easily enough (alternatively, we
	// could generate it based on the resolution and viewport, but we'd
	// need to be certain that we are always using the same values as the
	// game):
	matrix SVPositionToClip = mul(SVPositionToTranslatedWorld, TranslatedWorldToClip);

	// Create a stereo pair of SVPositionToTranslatedWorld matrices:
	l = mul(SVPositionToClip, l);
	r = mul(SVPositionToClip, r);

	// Transposing since we are writing directly to storage:
	modified_SVPositionToTranslatedWorld[0] = r._m00_m10_m20_m30;
	modified_SVPositionToTranslatedWorld[1] = r._m01_m11_m21_m31;
	modified_SVPositionToTranslatedWorld[2] = r._m02_m12_m22_m32;
	modified_SVPositionToTranslatedWorld[3] = r._m03_m13_m23_m33;
	modified_SVPositionToTranslatedWorld[4] = l._m00_m10_m20_m30;
	modified_SVPositionToTranslatedWorld[5] = l._m01_m11_m21_m31;
	modified_SVPositionToTranslatedWorld[6] = l._m02_m12_m22_m32;
	modified_SVPositionToTranslatedWorld[7] = l._m03_m13_m23_m33;

	// TODO: Create a modified version of the whole buffer, possibly with
	// other projection matrices modified to fix other effects
}
