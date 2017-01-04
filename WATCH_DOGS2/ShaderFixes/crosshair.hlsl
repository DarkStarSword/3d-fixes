// Depth buffer copied from other shaders to this input with 3Dmigoto:
Texture2D<float4> Viewport__DepthVPSampler__TexObj__ : register(t110);
Texture2DMS<float4> Viewport__DepthVPSamplerMS : register(t111);

cbuffer Viewport : register(b13)
{
  float4 CameraNearPlaneSize : packoffset(c0);
  float4x4 DepthTextureTransform : packoffset(c1);
  float4 FSMClipPlanes : packoffset(c5);
  float4 FacettedShadowCastParams : packoffset(c6);
  float4 FogValues0 : packoffset(c7);
  float4 FogValues1 : packoffset(c8);
  float4x4 InvProjectionMatrix : packoffset(c9);
  float4x4 InvProjectionMatrixDepth : packoffset(c13);
  float4x3 InvViewMatrix : packoffset(c17);
  float4x4 PreviousViewProjectionMatrix : packoffset(c20);
  float4x4 ProjectionMatrix : packoffset(c24);
  float4 RainOcclusionFadeParams : packoffset(c28);
  float4x4 RainOcclusionProjectionMatrix : packoffset(c29);
  float4 RainOcclusionShadowMapSize : packoffset(c33);
  float4 ReflectionVolumeDebugColors[15] : packoffset(c34);
  float4 VPosOffset : packoffset(c49);
  float4 VPosScale : packoffset(c50);
  float4x3 ViewMatrix : packoffset(c51);
  float4x4 ViewProjectionMatrix : packoffset(c54);
  float4x4 ViewRotProjectionMatrix : packoffset(c58);
  float4x4 ViewRotProjectionMatrixPure : packoffset(c62);
  float4 ViewportSize : packoffset(c66);

  struct
  {
    float near;
    float far;
    float view;
    float oneOverView;
  } CameraDistances : packoffset(c67);


  struct
  {
    float4x4 inverseTransform;
    float3 rcpFadeRangePositive;
    float textureArrayIndexAsFloat;
    float3 rcpFadeRangeNegative;
    float fadeFactor;
    float2 multipliers;
    uint parallaxCorrection;
    float padding0;
  } ReflectionVolumes[15] : packoffset(c68);

  float3 CameraDirection : packoffset(c173);
  float DefaultReflectionTextureArrayIndexAsFloat : packoffset(c173.w);
  float3 CameraPosition : packoffset(c174);
  float DynamicCubeMapReflectionTextureMaxMipIndex : packoffset(c174.w);
  float3 CullingCameraPosition : packoffset(c175);
  float ExposedWhitePointOverExposureScale : packoffset(c175.w);
  float3 FogColorVector : packoffset(c176);
  float ExposureScale : packoffset(c176.w);
  float3 OppositeFogColorDelta : packoffset(c177);
  float MaxParaboloidReflectionMipIndex : packoffset(c177.w);
  float3 SideFogColor : packoffset(c178);
  float MaxStaticReflectionMipIndex : packoffset(c178.w);
  float3 SunFogColorDelta : packoffset(c179);
  float MeasuredExposureScale : packoffset(c179.w);
  float3 TemporalFilteringParams : packoffset(c180);
  float RaindropRippleScale : packoffset(c180.w);
  float3 UncompressDepthWeights : packoffset(c181);
  float ReflectionScaleDistanceMul : packoffset(c181.w);
  float3 UncompressDepthWeightsWS : packoffset(c182);
  float ReflectionScaleStrength : packoffset(c182.w);
  float3 ViewPoint : packoffset(c183);
  float SkyParaboloidTextureMaxMipIndex : packoffset(c183.w);
  float2 DefaultReflectionMultipliers : packoffset(c184);
  bool UseOnlySkyReflection : packoffset(c184.z);
  float2 ReflectionGIControl : packoffset(c185);
  uint2 SelectedPixel : packoffset(c185.z);
}

float world_z_from_depth_buffer(float x, float y)
{
	uint width, height, samples = 0;
	float4 z;

	Viewport__DepthVPSampler__TexObj__.GetDimensions(width, height);
	if (width == 0)
		Viewport__DepthVPSamplerMS.GetDimensions(width, height, samples);

	x = min(max((x / 2 + 0.5) * width, 0), width - 1);
	y = min(max((-y / 2 + 0.5) * height, 0), height - 1);
	if (samples == 0)
		z.z = Viewport__DepthVPSampler__TexObj__.Load(int3(x, y, 0)).x;
	else
		z.z = Viewport__DepthVPSamplerMS.Load(int3(x, y, 0), 0).x;

	// Depth buffer scaling procedure copied from other shaders:
	z.x = dot(float2(z.z, 1), InvProjectionMatrix._m22_m32);
	z.y = dot(float2(z.z, 1), InvProjectionMatrix._m23_m33);
	return -z.x / z.y;
}

float adjust_from_depth_buffer(float x, float y)
{
	float4 stereo = StereoParams.Load(0);
	float separation = stereo.x; float convergence = stereo.y;
	float old_offset, offset, w, sampled_w, distance;
	uint i;

	// Stereo cursor: To improve the accuracy of the stereo cursor, we
	// sample a number of points on the depth buffer, starting at the near
	// clipping plane and working towards original x + separation.
	//
	// You can think of this as a line in three dimensional space that
	// starts at each eye and stretches out towards infinity. We sample 255
	// points along this line (evenly spaced in the X axis) and compare
	// with the depth buffer to find where the line is first intersected.
	//
	// Note: The reason for sampling 255 points came from a restriction in
	// DX9/SM3 where loops had to run a constant number of iterations and
	// there was no way to set that number from within the shader itself.
	// I'm not sure if the same restriction applies in DX11 with SM4/5 - if
	// it doesn't, we could change this to check each pixel instead for
	// better accuracy.
	//
	// Based on DarkStarSword's stereo crosshair code originally developed
	// for Miasmata, adapted to Unity, then translated to HLSL.

	offset = -convergence * separation;	// Z = X offset from center
	distance = separation - offset;	// Total distance to cover (separation - starting X offset)

	old_offset = offset;
	for (i = 0; i < 255; i++) {
		offset += distance / 255.0;

		// Calculate depth for this point on the line:
		w = (separation * convergence) / (separation - offset);

		sampled_w = world_z_from_depth_buffer(x + offset, y);
		if (sampled_w == 0)
			return 0;

		// If the sampled depth is closer than the calculated depth,
		// we have found something that intersects the line, so exit
		// the loop and return the last point that was not intersected:
		if (w > sampled_w)
			break;

		old_offset = offset;
	}

	return old_offset;
}

float adjust_from_stereo2mono_depth_buffer(float x, float y)
{
	float4 stereo = StereoParams.Load(0);
	float separation = stereo.x; float convergence = stereo.y;
	float old_offset, offset, w, left, right, left_sampled_w, right_sampled_w, sampled_w, distance;
	uint i;

	// Stereo cursor: To improve the accuracy of the stereo cursor, we
	// sample a number of points on the depth buffer, starting at the near
	// clipping plane and working towards original x + separation.
	//
	// You can think of this as a line in three dimensional space that
	// starts at each eye and stretches out towards infinity. We sample 255
	// points along this line (evenly spaced in the X axis) and compare
	// with the depth buffer to find where the line is first intersected.
	//
	// This particular variant uses the depth information from both eyes
	// (using 3DMigoto's stereo2mono feature) so we can find where the
	// lines from both eyes are intersected simultaneously for a more
	// accurate adjustment.
	//
	// Note: The reason for sampling 255 points came from a restriction in
	// DX9/SM3 where loops had to run a constant number of iterations and
	// there was no way to set that number from within the shader itself.
	// I'm not sure if the same restriction applies in DX11 with SM4/5 - if
	// it doesn't, we could change this to check each pixel instead for
	// better accuracy.
	//
	// Based on DarkStarSword's stereo crosshair code originally developed
	// for Miasmata, adapted to Unity, translated to HLSL, then updated to
	// make use of 3DMigoto's stereo2mono feature.

	float asep = abs(separation);
	float min_depth = IniParams.Load(0).y;

	offset = (min_depth - convergence) * asep;	// Z = X offset from center
	if (min_depth) // Avoid divide by 0
		offset /= min_depth;
	distance = asep - offset;			// Total distance to cover (asep - starting X offset)

	old_offset = offset;
	for (i = 0; i < 255; i++) {
		offset += distance / 255.0;

		// Calculate depth for this point on the line:
		w = (asep * convergence) / (asep - offset);

		float left = max((x - offset) / 2 + 0.5, 0);
		float right = min((x + offset) / 2 - 0.5, 0);

		left_sampled_w = world_z_from_depth_buffer(left, y);
		right_sampled_w = world_z_from_depth_buffer(right, y);

		// Only adjust the crosshair once it has intersected something in *both* eyes:
		sampled_w = max(left_sampled_w, right_sampled_w);

		// Adjust crosshair in both eyes once it intersects something in *either* eye:
		//sampled_w = min(left_sampled_w, right_sampled_w);

		// Equivalent to normal auto depth adjustment for a regular stereo depth buffer:
		//sampled_w = world_z_from_depth_buffer(x + offset * -stereo.z, y);

		// Equivalent to normal auto depth adjustment for a 2x width mono depth buffer:
		//sampled_w = world_z_from_depth_buffer((x + offset * -stereo.z) / 2 - 0.5 * -stereo.z, y);

		if (sampled_w == 0)
			return 0;

		// If the sampled depth is closer than the calculated depth,
		// we have found something that intersects the line, so exit
		// the loop and return the last point that was not intersected:
		if (w > sampled_w)
			break;

		old_offset = offset;
	}

	return old_offset * -stereo.z;
}
