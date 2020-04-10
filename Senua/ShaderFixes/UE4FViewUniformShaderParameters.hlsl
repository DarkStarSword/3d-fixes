// These control known variations in the structure definition. This can be game
// specific and you might need to study the constant buffer with my debug
// shader to work out if the specific game you are looking at has altered it in
// some other way.
#define NEW_UE4
#define SENUA

// Mapping of UE4 types into HLSL. half isn't specified like this in UE4 and we
// just turn them into regular floats anyway, but still leaving in the tags
// incase this ever gets adapted to something where half precision matters
typedef row_major matrix FMatrix;
typedef float2 FVector2D;
typedef float2 FVector2D_half;
typedef float3 FVector;
typedef float3 FVector_half;
typedef float4 FVector4;
typedef float4 FVector4_half;
typedef float4 FLinearColor;
typedef float4 FLinearColor_half;
typedef int int32;
typedef uint uint32;
typedef float float_half;

// Engine/Source/Runtime/Renderer/Public/GlobalDistanceFieldParameters.h:
#define GMaxGlobalDistanceFieldClipmaps 4
// Engine/Source/Runtime/Engine/Public/SceneView.h:
#define TVC_MAX 2

// UnrealEngine/Engine/Source/Runtime/Engine/Public/SceneView.h
// UnrealEngine/Engine/Source/Runtime/Engine/Private/SceneView.cpp
// Note that since this is used for a UAV structure definition we need to
// manually pad it so that it will match the HLSL constant buffer packing:
// https://msdn.microsoft.com/en-us/library/windows/desktop/bb509632(v=vs.85).aspx
struct FViewUniformShaderParameters {
	/*   0[4]  */ FMatrix TranslatedWorldToClip;
	/*   4[4]  */ FMatrix WorldToClip;
	/*   8[4]  */ FMatrix TranslatedWorldToView;
	/*  12[4]  */ FMatrix ViewToTranslatedWorld;
	/*  16[4]  */ FMatrix TranslatedWorldToCameraView;
	/*  20[4]  */ FMatrix CameraViewToTranslatedWorld;
	/*  24[4]  */ FMatrix ViewToClip;
	/*  28[4]  */ FMatrix ClipToView;
	/*  32[4]  */ FMatrix ClipToTranslatedWorld;
	/*  36[4]  */ FMatrix SVPositionToTranslatedWorld; // Variant of ClipToTranslatedWorld that includes a resolution divide
	/*  40[4]  */ FMatrix ScreenToWorld;
	/*  44[4]  */ FMatrix ScreenToTranslatedWorld;

	/*  48.xyz */ FVector_half ViewForward;
	/* PAD.w   */ float UAV_PADDING_ViewForward;
	/*  49.xyz */ FVector_half ViewUp;
	/* PAD.w   */ float UAV_PADDING_ViewUp;
	/*  50.xyz */ FVector_half ViewRight;
	/* PAD.w   */ float UAV_PADDING_ViewRight;
#ifdef NEW_UE4
	// Newer versions of UE4 only (if not sure, check if these match the
	// values in ViewUp/Right with no HMD present):
	/*  51.xyz */ FVector_half HMDViewNoRollUp;
	/* PAD.w   */ float UAV_PADDING_HMDViewNoRollUp;
	/*  52.xyz */ FVector_half HMDViewNoRollRight;
	/* PAD.w   */ float UAV_PADDING_HMDViewNoRollRight;
#endif
	/*  53     */ FVector4 InvDeviceZToWorldZTransform;
	/*  54     */ FVector4_half ScreenPositionScaleBias;
#ifdef SENUA
	// Senua's Sacrifice specific - same as ScreenPositionScaleBias?
	/*  55     */ FVector4_half senua_specific_56;
#endif
	/*  56.xyz */ FVector WorldCameraOrigin;
	/* PAD.w   */ float UAV_PADDING_WorldCameraOrigin;
	/*  57.xyz */ FVector TranslatedWorldCameraOrigin;
	/* PAD.w   */ float UAV_PADDING_TranslatedWorldCameraOrigin;
	/*  58.xyz */ FVector WorldViewOrigin;
	/* PAD.w   */ float UAV_PADDING_WorldViewOrigin;
	/*  59.xyz */ FVector PreViewTranslation;
	/* PAD.w   */ float UAV_PADDING_PreViewTranslation;

	/*  60[4]  */ FMatrix PrevProjection;
	/*  64[4]  */ FMatrix PrevViewProj;
	/*  68[4]  */ FMatrix PrevViewRotationProj;
	/*  72[4]  */ FMatrix PrevViewToClip;
	/*  76[4]  */ FMatrix PrevClipToView;
	/*  80[4]  */ FMatrix PrevTranslatedWorldToClip;
	/*  84[4]  */ FMatrix PrevTranslatedWorldToView;
	/*  88[4]  */ FMatrix PrevViewToTranslatedWorld;
	/*  92[4]  */ FMatrix PrevTranslatedWorldToCameraView;
	/*  96[4]  */ FMatrix PrevCameraViewToTranslatedWorld;

	/* 100.xyz */ FVector PrevWorldCameraOrigin;
	/* PAD.w   */ float UAV_PADDING_PrevWorldCameraOrigin;
	/* 101.xyz */ FVector PrevWorldViewOrigin;
	/* PAD.w   */ float UAV_PADDING_PrevWorldViewOrigin;
	/* 102.xyz */ FVector PrevPreViewTranslation;
	/* PAD.w   */ float UAV_PADDING_PrevPreViewTranslation;

	/* 103[4]  */ FMatrix PrevInvViewProj;
	/* 107[4]  */ FMatrix PrevScreenToTranslatedWorld;
#ifdef SENUA
	// Senua's Sacrifice specific. Looks like a duplicate of PrevViewProj
	// (or TranslatedWorldToClip). I bet I know what happened - UE4's
	// inconsistent matrix naming scheme confused the devs and they didn't
	// realise that "PrevTranslatedWorldToClip" was already present under
	// the name "PrevViewProj", so they added a second copy of it:
	/* 111[4]  */ FMatrix senua_specific_111;
#endif
	/* 115[4]  */ FMatrix ClipToPrevClip;

#ifdef NEW_UE4
	// Newer UE4 versions have more fields after this point
	/* 119     */ FVector4 GlobalClippingPlane;
	/* 120.xy  */ FVector2D FieldOfViewWideAngles;
	/* 120.zw  */ FVector2D PrevFieldOfViewWideAngles;
	/* 121     */ FVector4_half ViewRectMin;
	/* 122     */ FVector4 ViewSizeAndInvSize;
	/* 123     */ FVector4 BufferSizeAndInvSize;
	/* 124.x   */ int32 NumSceneColorMSAASamples;
	/* PAD.yzw */ float3 UAV_PADDING_NumSceneColorMSAASamples;
	/* 125     */ FVector4_half ExposureScale;
	/* 126     */ FVector4_half DiffuseOverrideParameter;
	/* 127     */ FVector4_half SpecularOverrideParameter;

#ifdef ALLOW_LARGE_STRUCTURES
	// Structured buffers cannot have a stride above 2048. If we need to
	// modify anything beyond this point we will have to access these in
	// some other way.

	/* 128     */ FVector4_half NormalOverrideParameter;
	/* 129.xy  */ FVector2D_half RoughnessOverrideParameter;
	/* 129.z   */ float PrevFrameGameTime;
	/* 129.w   */ float PrevFrameRealTime;
	/* 130.x   */ float_half OutOfBoundsMask;
	/* PAD.yzw */ float3 UAV_PADDING_OutOfBoundsMask;
	/* 131.xyz */ FVector WorldCameraMovementSinceLastFrame;
	/* 131.w   */ float CullingSign;
	/* 132.x   */ float_half NearPlane;
	/* 132.y   */ float AdaptiveTessellationFactor;
	/* 132.z   */ float GameTime;
	/* 132.w   */ float RealTime;

	// Note the CB debug shader will show these uints as 0:
	/* 133.x   */ uint32 Random;
	/* 133.y   */ uint32 FrameNumber;
	/* 133.z   */ uint32 StateFrameIndexMod8;
	/* 133.w   */ float_half CameraCut;
	/* 134.x   */ float_half UnlitViewmodeMask;
	/* PAD.yzw */ float3 UAV_PADDING_UnlitViewmodeMask;
	/* 135     */ FLinearColor_half DirectionalLightColor;
	/* 136     */ FVector_half DirectionalLightDirection;
	/* 137[2]  */ FVector4 TranslucencyLightingVolumeMin[TVC_MAX];
	/* 139[2]  */ FVector4 TranslucencyLightingVolumeInvSize[TVC_MAX];
	/* 141     */ FVector4 TemporalAAParams;
	/* 142     */ FVector4 CircleDOFParams;
	/* 143.x   */ float DepthOfFieldSensorWidth;
	/* 143.y   */ float DepthOfFieldFocalDistance;
	/* 143.z   */ float DepthOfFieldScale;
	/* 143.w   */ float DepthOfFieldFocalLength;
	/* 144.x   */ float DepthOfFieldFocalRegion;
	/* 144.y   */ float DepthOfFieldNearTransitionRegion;
	/* 144.z   */ float DepthOfFieldFarTransitionRegion;
	/* 144.w   */ float MotionBlurNormalizedToPixel;
	/* 145.x   */ float bSubsurfacePostprocessEnabled;
	/* 145.y   */ float GeneralPurposeTweak;
	/* 145.z   */ float_half DemosaicVposOffset;
	/* 146.xyz */ FVector IndirectLightingColorScale;
	/* 146.w   */ float_half HDR32bppEncodingMode;
	/* 147.xyz */ FVector AtmosphericFogSunDirection;
	/* 147.w   */ float_half AtmosphericFogSunPower;
	/* 148.x   */ float_half AtmosphericFogPower;
	/* 148.y   */ float_half AtmosphericFogDensityScale;
	/* 148.z   */ float_half AtmosphericFogDensityOffset;
	/* 148.w   */ float_half AtmosphericFogGroundOffset;
	/* 149.x   */ float_half AtmosphericFogDistanceScale;
	/* 149.y   */ float_half AtmosphericFogAltitudeScale;
	/* 149.z   */ float_half AtmosphericFogHeightScaleRayleigh;
	/* 149.w   */ float_half AtmosphericFogStartDistance;
	/* 150.x   */ float_half AtmosphericFogDistanceOffset;
	/* 150.y   */ float_half AtmosphericFogSunDiscScale;
	/* 150.z   */ uint32 AtmosphericFogRenderMask;
	/* 150.w   */ uint32 AtmosphericFogInscatterAltitudeSampleNum;
	/* 151     */ FLinearColor AtmosphericFogSunColor;
	/* 152.xyz */ FVector NormalCurvatureToRoughnessScaleBias;
	/* 152.w   */ float RenderingReflectionCaptureMask;
	/* 153     */ FLinearColor AmbientCubemapTint;
	/* 154.x   */ float AmbientCubemapIntensity;
	/* 154.y   */ float SkyLightParameters;
	/* PAD.zw  */ float UAV_PADDING_SkyLightParameters;
	/* 155     */ FVector4 SceneTextureMinMax;
	/* 156     */ FLinearColor SkyLightColor;
	/* 157[7]  */ FVector4 SkyIrradianceEnvironmentMap[7];
	/* 164.x   */ float MobilePreviewMode;
	/* 164.y   */ float HMDEyePaddingOffset;
	/* 164.z   */ float_half ReflectionCubemapMaxMip;
	/* 164.w   */ float ShowDecalsMask;
	/* 165.x   */ uint32 DistanceFieldAOSpecularOcclusionMode;
	/* 165.y   */ float IndirectCapsuleSelfShadowingIntensity;
	/* PAD.zw  */ float UAV_PADDING_IndirectCapsuleSelfShadowingIntensity;
	/* 166.xyz */ FVector ReflectionEnvironmentRoughnessMixingScaleBiasAndLargestWeight;
	/* 166.w   */ int32 StereoPassIndex;
	/* 167[4]  */ FVector4 GlobalVolumeCenterAndExtent_UB[GMaxGlobalDistanceFieldClipmaps];
	/* 171[4]  */ FVector4 GlobalVolumeWorldToUVAddAndMul_UB[GMaxGlobalDistanceFieldClipmaps];
	/* 175.x   */ float GlobalVolumeDimension_UB;
	/* 176.y   */ float GlobalVolumeTexelSize_UB;
	/* 176.z   */ float MaxGlobalDistance_UB;
	/* 176.w   */ float bCheckerboardSubsurfaceProfileRendering;
#endif /* ALLOW_LARGE_STRUCTURES */
#endif
};
