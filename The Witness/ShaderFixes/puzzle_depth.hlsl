// Called from b9ee699c92cfd6e6

void main(
  float3 v0 : TEXCOORD0,
  float w0 : TEXCOORD7,
  float4 v1 : TEXCOORD1,
  float4 v2 : TEXCOORD2,
  float4 v3 : COLOR0,
  float4 v4 : COLOR1,
  float4 v5 : SV_Position0,

// New input from vertex shader 28d7da4797f5c715:
float depth : TEXCOORD3,

  uint v6 : SV_IsFrontFace0,
  out float o0 : SV_Target0)
{
	o0 = depth;
}
