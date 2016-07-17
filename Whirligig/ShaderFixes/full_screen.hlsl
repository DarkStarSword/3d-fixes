void main(
		out float4 pos : SV_Position0,
		out float2 texcoord : TEXCOORD0,
		uint vertex : SV_VertexID)
{
	// Not using vertex buffers so manufacture our own coordinates.
	// You may have to adjust this depending on whether the game is using
	// clockwise or counterclockwise for front-facing surfaces:
	switch(vertex) {
		case 0:
			pos.xy = float2(-1, -1);
			break;
		case 1:
			pos.xy = float2(1, -1);
			break;
		case 2:
			pos.xy = float2(-1, 1);
			break;
		case 3:
			pos.xy = float2(-1, 1);
			break;
		case 4:
			pos.xy = float2(1, -1);
			break;
		case 5:
			pos.xy = float2(1, 1);
			break;
		default:
			pos.xy = 0;
			break;
	};
	pos.zw = float2(0, 1);
	texcoord = pos.xy * float2(1, -1);
}
