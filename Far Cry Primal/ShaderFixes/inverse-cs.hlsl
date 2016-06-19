// Definition copied from another shader:
cbuffer CViewportShaderParameterProvider : register(b0)
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

RWBuffer<float4> InvViewMatrixOutputBuffer : register(u0);

float4 inverse_transpose_parallel(matrix m, uint pos)
{
	uint3 idx;
	float4 tmp;

	idx = pos < uint3(1, 2, 3) ? uint3(1, 2, 3) : uint3(0, 1, 2);
	float add = pos % 2 == 0 ? 1.0 : -1.0;

	tmp = m[idx.x].yxxx*(add*m[idx.y].zwyz*m[idx.z].wzwy - add*m[idx.y].wzwy*m[idx.z].zwyz)
	    + m[idx.x].zzyy*(add*m[idx.y].wxwx*m[idx.z].ywxz - add*m[idx.y].ywxz*m[idx.z].wxwx)
	    + m[idx.x].wwwz*(add*m[idx.y].yzxy*m[idx.z].zxyx - add*m[idx.y].zxyx*m[idx.z].yzxy);
	return tmp / determinant(m);
}

[numthreads(4, 1, 1)]
void main(uint3 tid: SV_DispatchThreadID)
{
	// We're using a transposing version of the matrix inverse function.
	// This may seem wrong at first glance, but it works so long as the
	// input matrix is declared in "column_major" order, because DX11
	// stores "column_major" matrices with the entries across each *row* in
	// each of the register components (this is the opposite of DX9), but
	// when we write it to the output buffer we are writing the entries
	// down each *column* to each of the components in a register. When
	// this is read back in the destination shader, it will have been
	// effectively transposed back to the correct order.
	//
	// If the input matrix is declared to be in "row_major" order, just lie
	// and declare it "column_major" so the compiler will do the right
	// thing, or add a transpose() around the input matrix (transposing the
	// output would require a synchronisation between threads - better to
	// avoid that and just transpose the input, which should be
	// mathematically equivalent). Note that if you legitimately wanted a
	// transposed output for some reason you could save some (13)
	// instructions in this shader by doing the opposite of this advice.
	InvViewMatrixOutputBuffer[tid.x] = inverse_transpose_parallel(ViewMatrix, tid.x);
}
