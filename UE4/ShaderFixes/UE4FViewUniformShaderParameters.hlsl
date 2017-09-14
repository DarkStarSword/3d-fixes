// These control known variations in the structure definition. This can be game
// specific and you might need to study the constant buffer with my debug
// shader to work out if the specific game you are looking at has altered it in
// some other way.
#define NEW_UE4
#undef SENUA

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
	/*  55.xyz */ FVector WorldCameraOrigin;
	/* PAD.w   */ float UAV_PADDING_WorldCameraOrigin;
	/*  56.xyz */ FVector TranslatedWorldCameraOrigin;
	/* PAD.w   */ float UAV_PADDING_TranslatedWorldCameraOrigin;
	/*  57.xyz */ FVector WorldViewOrigin;
	/* PAD.w   */ float UAV_PADDING_WorldViewOrigin;
	/*  58.xyz */ FVector PreViewTranslation;
	/* PAD.w   */ float UAV_PADDING_PreViewTranslation;

	/*  59[4]  */ FMatrix PrevProjection;
	/*  63[4]  */ FMatrix PrevViewProj;
	/*  67[4]  */ FMatrix PrevViewRotationProj;
	/*  71[4]  */ FMatrix PrevViewToClip;
	/*  75[4]  */ FMatrix PrevClipToView;
	/*  79[4]  */ FMatrix PrevTranslatedWorldToClip;
	/*  83[4]  */ FMatrix PrevTranslatedWorldToView;
	/*  87[4]  */ FMatrix PrevViewToTranslatedWorld;
	/*  91[4]  */ FMatrix PrevTranslatedWorldToCameraView;
	/*  95[4]  */ FMatrix PrevCameraViewToTranslatedWorld;

	/*  99.xyz */ FVector PrevWorldCameraOrigin;
	/* PAD.w   */ float UAV_PADDING_PrevWorldCameraOrigin;
	/* 100.xyz */ FVector PrevWorldViewOrigin;
	/* PAD.w   */ float UAV_PADDING_PrevWorldViewOrigin;
	/* 101.xyz */ FVector PrevPreViewTranslation;
	/* PAD.w   */ float UAV_PADDING_PrevPreViewTranslation;

	/* 102[4]  */ FMatrix PrevInvViewProj;
	/* 106[4]  */ FMatrix PrevScreenToTranslatedWorld;
#ifdef SENUA
	// Senua's Sacrifice specific. Looks like a duplicate of PrevViewProj
	// (or TranslatedWorldToClip). I bet I know what happened - UE4's
	// inconsistent matrix naming scheme confused the devs and they didn't
	// realise that "PrevTranslatedWorldToClip" was already present under
	// the name "PrevViewProj", so they added a second copy of it:
	/* 111[4]  */ FMatrix senua_specific_111;
#endif
	/* 110[4]  */ FMatrix ClipToPrevClip;

#ifdef NEW_UE4
	// Newer UE4 versions have more fields after this point
	/* 114     */ FVector4 GlobalClippingPlane;
	/* 115.xy  */ FVector2D FieldOfViewWideAngles;
	/* 115.zw  */ FVector2D PrevFieldOfViewWideAngles;
	/* 116     */ FVector4_half ViewRectMin;
	/* 117     */ FVector4 ViewSizeAndInvSize;
	/* 118     */ FVector4 BufferSizeAndInvSize;
	/* 119.x   */ int32 NumSceneColorMSAASamples;
	/* PAD.yzw */ float3 UAV_PADDING_NumSceneColorMSAASamples;
	/* 120     */ FVector4_half ExposureScale;
	/* 121     */ FVector4_half DiffuseOverrideParameter;
	/* 122     */ FVector4_half SpecularOverrideParameter;

#ifdef ALLOW_LARGE_STRUCTURES
	// Structured buffers cannot have a stride above 2048. If we need to
	// modify anything beyond this point we will have to access these in
	// some other way.

	/* 123     */ FVector4_half NormalOverrideParameter;
	/* 124.xy  */ FVector2D_half RoughnessOverrideParameter;
	/* 124.z   */ float PrevFrameGameTime;
	/* 124.w   */ float PrevFrameRealTime;
	/* 125.x   */ float_half OutOfBoundsMask;
	/* PAD.yzw */ float3 UAV_PADDING_OutOfBoundsMask;
	/* 126.xyz */ FVector WorldCameraMovementSinceLastFrame;
	/* 126.w   */ float CullingSign;
	/* 127.x   */ float_half NearPlane;
	/* 127.y   */ float AdaptiveTessellationFactor;
	/* 127.z   */ float GameTime;
	/* 127.w   */ float RealTime;

	// Note the CB debug shader will show these uints as 0:
	/* 128.x   */ uint32 Random;
	/* 128.y   */ uint32 FrameNumber;
	/* 128.z   */ uint32 StateFrameIndexMod8;
	/* 128.w   */ float_half CameraCut;
	/* 129.x   */ float_half UnlitViewmodeMask;
	/* PAD.yzw */ float3 UAV_PADDING_UnlitViewmodeMask;
	/* 130     */ FLinearColor_half DirectionalLightColor;
	/* 131     */ FVector_half DirectionalLightDirection;
	/* 132[2]  */ FVector4 TranslucencyLightingVolumeMin[TVC_MAX];
	/* 134[2]  */ FVector4 TranslucencyLightingVolumeInvSize[TVC_MAX];
	/* 136     */ FVector4 TemporalAAParams;
	/* 137     */ FVector4 CircleDOFParams;
	/* 138.x   */ float DepthOfFieldSensorWidth;
	/* 138.y   */ float DepthOfFieldFocalDistance;
	/* 138.z   */ float DepthOfFieldScale;
	/* 138.w   */ float DepthOfFieldFocalLength;
	/* 139.x   */ float DepthOfFieldFocalRegion;
	/* 139.y   */ float DepthOfFieldNearTransitionRegion;
	/* 139.z   */ float DepthOfFieldFarTransitionRegion;
	/* 139.w   */ float MotionBlurNormalizedToPixel;
	/* 140.x   */ float bSubsurfacePostprocessEnabled;
	/* 140.y   */ float GeneralPurposeTweak;
	/* 140.z   */ float_half DemosaicVposOffset;
	/* 141.xyz */ FVector IndirectLightingColorScale;
	/* 141.w   */ float_half HDR32bppEncodingMode;
	/* 142.xyz */ FVector AtmosphericFogSunDirection;
	/* 142.w   */ float_half AtmosphericFogSunPower;
	/* 143.x   */ float_half AtmosphericFogPower;
	/* 143.y   */ float_half AtmosphericFogDensityScale;
	/* 143.z   */ float_half AtmosphericFogDensityOffset;
	/* 143.w   */ float_half AtmosphericFogGroundOffset;
	/* 144.x   */ float_half AtmosphericFogDistanceScale;
	/* 144.y   */ float_half AtmosphericFogAltitudeScale;
	/* 144.z   */ float_half AtmosphericFogHeightScaleRayleigh;
	/* 144.w   */ float_half AtmosphericFogStartDistance;
	/* 145.x   */ float_half AtmosphericFogDistanceOffset;
	/* 145.y   */ float_half AtmosphericFogSunDiscScale;
	/* 145.z   */ uint32 AtmosphericFogRenderMask;
	/* 145.w   */ uint32 AtmosphericFogInscatterAltitudeSampleNum;
	/* 146     */ FLinearColor AtmosphericFogSunColor;
	/* 147.xyz */ FVector NormalCurvatureToRoughnessScaleBias;
	/* 147.w   */ float RenderingReflectionCaptureMask;
	/* 148     */ FLinearColor AmbientCubemapTint;
	/* 149.x   */ float AmbientCubemapIntensity;
	/* 149.y   */ float SkyLightParameters;
	/* PAD.zw  */ float UAV_PADDING_SkyLightParameters;
	/* 150     */ FVector4 SceneTextureMinMax;
	/* 151     */ FLinearColor SkyLightColor;
	/* 152[7]  */ FVector4 SkyIrradianceEnvironmentMap[7];
	/* 159.x   */ float MobilePreviewMode;
	/* 159.y   */ float HMDEyePaddingOffset;
	/* 159.z   */ float_half ReflectionCubemapMaxMip;
	/* 159.w   */ float ShowDecalsMask;
	/* 160.x   */ uint32 DistanceFieldAOSpecularOcclusionMode;
	/* 160.y   */ float IndirectCapsuleSelfShadowingIntensity;
	/* PAD.zw  */ float UAV_PADDING_IndirectCapsuleSelfShadowingIntensity;
	/* 161.xyz */ FVector ReflectionEnvironmentRoughnessMixingScaleBiasAndLargestWeight;
	/* 161.w   */ int32 StereoPassIndex;
	/* 162[4]  */ FVector4 GlobalVolumeCenterAndExtent_UB[GMaxGlobalDistanceFieldClipmaps];
	/* 166[4]  */ FVector4 GlobalVolumeWorldToUVAddAndMul_UB[GMaxGlobalDistanceFieldClipmaps];
	/* 170.x   */ float GlobalVolumeDimension_UB;
	/* 171.y   */ float GlobalVolumeTexelSize_UB;
	/* 171.z   */ float MaxGlobalDistance_UB;
	/* 171.w   */ float bCheckerboardSubsurfaceProfileRendering;
#endif /* ALLOW_LARGE_STRUCTURES */
#endif
};
