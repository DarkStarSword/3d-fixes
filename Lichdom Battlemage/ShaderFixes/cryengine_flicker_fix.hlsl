Texture2D<float4> _tex0 : register(t0);

void main(
  float4 v0 : SV_Position0,
  float2 v1 : TEXCOORD0,
  out float4 o0 : SV_Target0)
{
	float width, height;

	_tex0.GetDimensions(width, height);
	float4 right = _tex0.Load(int3(v0.xy, 0));
	float4 left = _tex0.Load(int3(v0.x + width / 2, v0.y, 0));
	o0 = max(left, right);
}
