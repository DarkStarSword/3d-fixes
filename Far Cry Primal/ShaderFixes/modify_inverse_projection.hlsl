cbuffer CDepthReconstructionProvider : register(b3)
{
  float4x4 InvViewRotProjectionMatrix : packoffset(c0);
  float4x4 ReconsInvViewRotProjectionMatrix : packoffset(c4);
  float3 ReconsCamPosition : packoffset(c8);
  float ReconsDepthMul : packoffset(c8.w);
  float ReconsDepthOffset : packoffset(c9);
  float ReconsViewFar : packoffset(c9.y);
  float ReconsViewNear : packoffset(c9.z);
  float ReconsViewOORange : packoffset(c9.w);
  float ReconsViewRange : packoffset(c10);
}

RWBuffer<float4> modified_projection_composite : register(u0);

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

	matrix im = InvViewRotProjectionMatrix;

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
	// (called ISP): 1/SP * P * 1/P * 1/V * 1/M
	//
	// But matrix maths allows us to do the 1/SP * P multiplication first,
	// so if we can find that matrix then we would have a single matrix
	// that we can multiply any inverse MVP, inverse VP or inverse P matrix
	// by to inject a stereo correction.
	//
	// But since we don't necessarily know P or 1/P so we have to find an
	// equivelent matrix. We do know about the structure of a typical
	// projection matrix so with a bit of maths we can find that this
	// matrix is equivelent to 1/SP * P. As it turns out, this matrix is
	// remarkably similar to the forwards variant, just that a few fields
	// are negated:
	//
	// [                      1, 0, 0, 0 ],
	// [                      0, 1, 0, 0 ],
	// [ -(sep*conv) / (q*near), 0, 1, 0 ],
	// [ -sep + (sep*conv)/near, 0, 0, 1 ]
	//   where q = far / (far - near)
	//
	// But we still need to know the near and far clipping planes to create
	// this matrix. If we had a pure projection matrix deriving them would
	// be straight forward, but since it may be a composite matrix we need
	// to employ another maths trick. We can derive those values by
	// inversing whatever matrix we do have and running a coordinate with Z
	// = 0 and Z = 1 through it, normalising the result then running that
	// back through the forwards matrix:

	matrix m = inverse(im); // Note that we are inversing an inverse - now a forwards
	float4 tmp;
	tmp = mul(float4(0, 0, 0, 1), im);
	float near = mul(tmp / tmp.w, m).w;
	tmp = mul(float4(0, 0, 1, 1), im);
	float far = mul(tmp / tmp.w, m).w;

	// Now we have the values we need to create our injection matrix:
	float q = far / (far - near);
	float e = -(sep*conv) / (q*near);
	float f = -sep + (sep*conv)/near;

	// And now we can multiply the MVP, VP or P matrix by our injection
	// matrix to inject the stereo correction. Since we are modifying an
	// inverse matrix, the injection matrix goes on the left:
	// [ 1, 0, 0, 0 ]   [ ax, ay, az, aw ]
	// [ 0, 1, 0, 0 ] x [ bx, by, bz, bw ]
	// [ e, 0, 1, 0 ]   [ cx, cy, cz, cw ]
	// [ f, 0, 0, 1 ]   [ dx, dy, dz, dw ]
	//
	//   [            ax,            ay,            az,            aw ]
	// = [            bx,            by,            bz,            bw ]
	//   [ (e * ax) + cx, (e * ay) + cy, (e * az) + cz, (e * aw) + cw ]
	//   [ (f * ax) + dx, (f * ay) + dy, (f * az) + dz, (f * aw) + dw ]

	matrix left = im, right = im;

	right[2] += e * im[0];
	right[3] += f * im[0];
	left[2]  -= e * im[0];
	left[3]  -= f * im[0];

	// Transposing since we are writing directly to storage:
	modified_projection_composite[0] = right._m00_m10_m20_m30;
	modified_projection_composite[1] = right._m01_m11_m21_m31;
	modified_projection_composite[2] = right._m02_m12_m22_m32;
	modified_projection_composite[3] = right._m03_m13_m23_m33;
	modified_projection_composite[4] =  left._m00_m10_m20_m30;
	modified_projection_composite[5] =  left._m01_m11_m21_m31;
	modified_projection_composite[6] =  left._m02_m12_m22_m32;
	modified_projection_composite[7] =  left._m03_m13_m23_m33;
}
