#define input_matrix_offset IniParams[0].x

Texture1D<float4> IniParams : register(t120);

#define MATRIX(cb, idx) matrix(cb[idx], cb[idx+1], cb[idx+2], cb[idx+3])

cbuffer InputConstantBuffer : register(b0)
{
	float4 input_cb[2048];
}

RWBuffer<float4> OutputMatrix : register(u0);

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
	matrix input_matrix = MATRIX(input_cb, input_matrix_offset);

	// Inversed matrix:
	OutputMatrix[tid.x] = inverse_transpose_parallel(transpose(input_matrix), tid.x);

	// Copy input matrix to output for convinence
	OutputMatrix[tid.x + 4] = input_cb[input_matrix_offset + tid.x];
}
