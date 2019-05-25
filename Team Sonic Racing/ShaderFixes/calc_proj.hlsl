cbuffer InputConstantBuffer : register(b0)
{
  row_major float4x4 gWorldViewProj; // Index:    0 1 2 3          Components:    16 [unused]
  row_major float3x4 gWorldView;     // Index:    4 5 6            Components:    12 [unused]
}

RWBuffer<float4> OutputMatrix : register(u0);

groupshared matrix iwv;

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
	iwv[tid.x] = inverse_transpose_parallel(matrix(gWorldView, float4(0,0,0,1)), tid.x);
	AllMemoryBarrierWithGroupSync();
	OutputMatrix[tid.x] = mul(iwv, gWorldViewProj)[tid.x];
}
