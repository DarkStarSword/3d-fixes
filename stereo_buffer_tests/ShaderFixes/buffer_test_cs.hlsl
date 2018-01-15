Texture2D<float4> StereoParams : register(t125);
Texture1D<float4> IniParams : register(t120);

RWBuffer<float> u0 : register(u0);
RWBuffer<float> u1 : register(u1);
RWBuffer<float> u2 : register(u2);
RWBuffer<float> u3 : register(u3);
RWStructuredBuffer<float> u4 : register(u4);
RWStructuredBuffer<float> u5 : register(u5);
RWStructuredBuffer<float> u6 : register(u6);
RWStructuredBuffer<float> u7 : register(u7);

[numthreads(1, 1, 1)]
void main()
{
	float result = StereoParams.Load(0).z;
	u0[0] = result;
	u1[0] = result;
	u2[0] = result;
	u3[0] = result;
	u4[0] = result;
	u5[0] = result;
	u6[0] = result;
	u7[0] = result;
}
