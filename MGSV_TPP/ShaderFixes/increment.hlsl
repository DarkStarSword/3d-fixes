struct transformation_buffer {
	matrix transformation;
	float time;
	float inc;
};

RWStructuredBuffer<transformation_buffer> transform : register(u0);

[numthreads(1, 1, 1)]
void main()
{
	transform[0].inc++;
}
