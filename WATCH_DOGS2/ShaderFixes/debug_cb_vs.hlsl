struct vs2gs {
	uint idx : TEXCOORD0;
};

void main(uint id : SV_VertexID, out vs2gs output)
{
	output.idx = id;
}
