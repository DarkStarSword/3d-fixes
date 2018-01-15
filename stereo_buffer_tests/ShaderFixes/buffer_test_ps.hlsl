Texture2D<float4> StereoParams : register(t125);
Texture1D<float4> IniParams : register(t120);

RWBuffer<float> uav : register(u3);

void main(out float result : SV_Target0, out float result1 : SV_Target1, out float result2 : SV_Target2)
{
	result = StereoParams.Load(0).z;
	result1 = result;
	result2 = result;
	uav[0] = result;
}
