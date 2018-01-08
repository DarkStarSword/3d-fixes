Texture2D<float> downscaled_zbuffer : register(t110);

Texture2D<float4> StereoParams : register(t125);
Texture1D<float4> IniParams : register(t120);

#define min_convergence IniParams[1].x
#define max_convergence IniParams[1].y
#define convergence_bias IniParams[1].z
#define slow_convergence_rate IniParams[1].w
#define slow_convergence_trigger IniParams[2].x
#define instant_convergence_trigger IniParams[2].y

// Copied from lighting shaders with 3DMigoto, definition from
// CGIncludes/UnityShaderVariables.cginc:
cbuffer UnityPerCamera : register(b13)
{
	// Time (t = time since current level load) values from Unity
	uniform float4 _Time; // (t/20, t, t*2, t*3)
	uniform float4 _SinTime; // sin(t/8), sin(t/4), sin(t/2), sin(t)
	uniform float4 _CosTime; // cos(t/8), cos(t/4), cos(t/2), cos(t)
	uniform float4 unity_DeltaTime; // dt, 1/dt, smoothdt, 1/smoothdt

	uniform float3 _WorldSpaceCameraPos;

	// x = 1 or -1 (-1 if projection is flipped)
	// y = near plane
	// z = far plane
	// w = 1/far plane
	uniform float4 _ProjectionParams;

	// x = width
	// y = height
	// z = 1 + 1.0/width
	// w = 1 + 1.0/height
	uniform float4 _ScreenParams;

	// Values used to linearize the Z buffer (http://www.humus.name/temp/Linearize%20depth.txt)
	// x = 1-far/near
	// y = far/near
	// z = x/far
	// w = y/far
	uniform float4 _ZBufferParams;

	// x = orthographic camera's width
	// y = orthographic camera's height
	// z = unused
	// w = 1.0 if camera is ortho, 0.0 if perspective
	uniform float4 unity_OrthoParams;
}

void main(out float convergence : SV_Target0)
{
	float target_convergence, convergence_difference;
	float current_convergence = StereoParams.Load(0).y;
	float z;

	z =     downscaled_zbuffer.Load(float3(0, 0, 0));
	z = max(downscaled_zbuffer.Load(float3(1, 0, 0)), z);
	z = max(downscaled_zbuffer.Load(float3(0, 1, 0)), z);
	z = max(downscaled_zbuffer.Load(float3(1, 1, 0)), z);

	target_convergence = 1 / (_ZBufferParams.z * z + _ZBufferParams.w);
	target_convergence = max(min(max(target_convergence, min_convergence), max_convergence) + convergence_bias, 0);

	convergence_difference = distance(target_convergence, current_convergence);
	if (convergence_difference >= instant_convergence_trigger) {
		convergence = target_convergence;
	} else if (convergence_difference >= slow_convergence_trigger) {
		if (target_convergence > current_convergence)
			convergence = min(target_convergence, current_convergence + slow_convergence_rate);
		else
			convergence = max(target_convergence, current_convergence - slow_convergence_rate);
	} else {
		convergence = 1.#QNAN;
	}
}
