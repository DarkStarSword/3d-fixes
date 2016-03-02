// Depth buffer copied from other shaders to this input with 3Dmigoto:
Texture2D<float4> ZBuffer : register(t110);

cbuffer CViewportShaderParameterProvider : register(b13)
{
  float4x4 InvProjectionMatrix : packoffset(c0);
  float4x4 InvViewMatrix : packoffset(c4);
  float4x4 ProjectionMatrix : packoffset(c8);
  float4x4 ViewMatrix : packoffset(c12);
  float4x4 ViewProjectionMatrix : packoffset(c16);
  float4x4 ViewRotProjectionMatrix : packoffset(c20);
  float4x4 ViewRotProjectionMatrix_Previous : packoffset(c24);
  float4 AmbientSHR : packoffset(c28);
  float4 AmbientSHG : packoffset(c29);
  float4 AmbientSHB : packoffset(c30);
  float4 CameraDistances : packoffset(c31);
  float4 CameraNearPlaneSize : packoffset(c32);
  float4 DepthScale : packoffset(c33);
  float4 DepthTextureScaleOffset : packoffset(c34);
  float4 FogParams : packoffset(c35);
  float4 FogSHB : packoffset(c36);
  float4 FogSHG : packoffset(c37);
  float4 FogSHR : packoffset(c38);
  float4 HeightFogParams : packoffset(c39);
  float4 ViewportSize : packoffset(c40);
  float3 ViewPoint : packoffset(c41);
  float3 CameraPosition : packoffset(c42);
  float3 CameraPosition_Previous : packoffset(c43);
  float3 CameraPositionFractions : packoffset(c44);
  float3 CameraPositionFractions_Previous : packoffset(c45);
  float3 CameraRight : packoffset(c46);
  float3 CameraUp : packoffset(c47);
  float3 CameraDirection : packoffset(c48);
  float3 EnvironmentMapColorOffset : packoffset(c49);
  float3 EnvironmentMapColorScale : packoffset(c50);
  float3 AmbientOcclusionRanges : packoffset(c51);
  float3 DepthTextureRcpSize : packoffset(c52);
  float2 MotionVectorOffsets : packoffset(c53);
  float2 DepthRangeCompression : packoffset(c53.z);
  float ShadowProjDepthMinValue : packoffset(c54);
  float DistanceScale : packoffset(c54.y);
  float WorldSpaceZOffset : packoffset(c54.z);
  float WorldSpaceZOffset_Previous : packoffset(c54.w);
  float CameraFOVDeg : packoffset(c55);
  float EffectsEmissiveEVBias : packoffset(c55.y);
  float ShadowCSMLastSliceIndex : packoffset(c55.z);
  float UseNormalization : packoffset(c55.w);
  float FogUndergroundColorScale : packoffset(c56);
}

float world_z_from_depth_buffer(float x, float y)
{
	uint width, height;
	float z;

	ZBuffer.GetDimensions(width, height);

	x = min(max((x / 2 + 0.5) * width, 0), width - 1);
	y = min(max((-y / 2 + 0.5) * height, 0), height - 1);
	z = ZBuffer.Load(int3(x, y, 0)).x;

	// Z buffer scaling copied from the lighting shaders:
	return CameraDistances.z / (DepthScale.y * z + DepthScale.x);
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
