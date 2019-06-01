// Mirror mode eye swap correction

Texture2D<float4> tex : register(t100);
Texture2D<float4> StereoParams : register(t125);

#ifdef VERTEX_SHADER
void main(
  float2 v0 : POSITION0,
  float2 v1 : TEXCOORD0,
  uint id : SV_VertexID,
  out float4 o0 : SV_Position0,
  out float2 o1 : TEXCOORD0,
  out float2 p1 : TEXCOORD1)
{
  o0.xy = v0.xy;
  o0.zw = float2(0,1);
  o1.xy = v1.xy;
  p1.xy = v0.xy * float2(0.5,-0.5) + float2(0.5,0.5);

	// Detect whether track mirroring is in effect. If it is we need to
	// swap eyes and continue, otherwise we bail out of this shader now. To
	// detect this we compare the position the game has passed in with the
	// expected texture coordinate. This works for vertices at the side of
	// the screen, but not those in the center of the screen.
	float u = v0.x * 0.5 + 0.5;
	if (abs(v1.x - u) < 0.1)
		o0 = 0;
}
#else
void main(
  float4 v0 : SV_Position0,
  float2 v1 : TEXCOORD0,
  float2 w1 : TEXCOORD1,
  out float4 o0 : SV_Target0)
{
	uint  width, height;
	float2 pos = v0.xy;

	tex.GetDimensions(width, height);

	float4 s = StereoParams.Load(0);
	if (s.z == -1)
		pos.x += width / 2;

	o0 = tex.Load(float3(pos, 0));
}
#endif
