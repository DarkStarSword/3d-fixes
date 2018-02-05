#define TRANSLATE_X IniParams[4].x
#define TRANSLATE_Y IniParams[4].y
#define TRANSLATE_Z IniParams[4].z
#define ROTATE_Y IniParams[4].w
#define TIME IniParams[5].x
#define TRANSLATE_SPEED IniParams[5].y
#define ROTATE_SPEED IniParams[5].z

struct transformation_buffer {
	matrix transformation;
	float time;
};

RWStructuredBuffer<transformation_buffer> transform : register(u0);

Texture1D<float4> IniParams : register(t120);

#include "matrix.hlsl"

[numthreads(1, 1, 1)]
void main()
{
	matrix m = transform[0].transformation;
	float delta = (TIME - transform[0].time);
	transform[0].time = TIME;

	float3 translate = float3(TRANSLATE_X, TRANSLATE_Y, TRANSLATE_Z) * delta * TRANSLATE_SPEED;
	m = mul(translation_matrix(translate.x, translate.y, translate.z), m);

	m = mul(rotation_y_matrix(-ROTATE_Y * ROTATE_SPEED), m);

	transform[0].transformation = m;
}
