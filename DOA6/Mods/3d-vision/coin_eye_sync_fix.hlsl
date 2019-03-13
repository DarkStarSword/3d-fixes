ByteAddressBuffer t100 : register(t100);
ByteAddressBuffer t101 : register(t101);

RWByteAddressBuffer u0 : register(u0);
RWByteAddressBuffer u1 : register(u1);

[numthreads(1, 1, 1)]
void main(uint3 tid: SV_DispatchThreadID)
{
	u0.Store4(tid.x * 16, t100.Load4(tid.x * 16));
	u1.Store4(tid.x * 16, t101.Load4(tid.x * 16));
}
