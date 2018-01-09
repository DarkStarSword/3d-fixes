Texture2D<float> downscaled_zbuffer : register(t110);

Texture2D<float4> StereoParams : register(t125);
Texture1D<float4> IniParams : register(t120);

#define min_convergence IniParams[1].x
#define max_convergence_soft IniParams[1].y
#define max_convergence_hard IniParams[1].z
#define popout IniParams[1].w
#define slow_convergence_rate IniParams[2].x
#define slow_convergence_threshold_near IniParams[2].y
#define slow_convergence_threshold_far IniParams[2].z
#define instant_convergence_threshold IniParams[2].w
#define time IniParams[3].x
#define prev_time IniParams[3].y
#define anti_judder_threshold IniParams[3].w

struct auto_convergence_state {
	float4 last_convergence;
};

RWStructuredBuffer<struct auto_convergence_state> state : register(u1);

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

void main(out float auto_convergence : SV_Target0)
{
	float target_convergence, convergence_difference;
	float current_convergence = StereoParams.Load(0).y;
	float z, w;

	float4 stereo = StereoParams.Load(0);
	float separation = stereo.x, convergence = stereo.y, eye = stereo.z, raw_sep = stereo.w;

	z =     downscaled_zbuffer.Load(float3(0, 0, 0));
	z = max(downscaled_zbuffer.Load(float3(1, 0, 0)), z);
	z = max(downscaled_zbuffer.Load(float3(0, 1, 0)), z);
	z = max(downscaled_zbuffer.Load(float3(1, 1, 0)), z);
	w = 1 / (_ZBufferParams.z * z + _ZBufferParams.w);

	// A lot of the maths below is experimental to try to find a good
	// auto-convergence algorithm that works well with a wide variety of
	// screen sizes, seating distances, and varying scenes in the game.

	// Apply the max convergence now, before we apply the popout bias, on
	// the theory that the max suitable convergence is going to vary based
	// on screen size
	target_convergence = min(w, max_convergence_soft);

	// Apply the popout bias. This experimental formula is derived by
	// taking the nvidia formula with the perspective divide and the
	// original x=0:
	//
	//   x' = x + separation * (depth - convergence) / depth
	//   x' = separation * (depth - convergence) / depth
	//
	// That gives us our original stereo corrected X value using a
	// convergence that would place the closest object at screen depth
	// (barring the result of capping the convergence). We want to find a
	// new convergence value that would instead position the object
	// slightly popped out - to do so in a way that is comfortable
	// regardless of scene, screen size, and player distance from the
	// screen we apply the popout bias to the x', call it x''. Because we
	// are modifying this post-separation, we will need to multiply by the
	// raw separation value so that it scales with separation (otherwise we
	// would always end with the full pop-out regardless of separation -
	// which is actually kind of cool - people who like toyification might
	// appreciate it, but we do want turning the stereo effect down to
	// reduce the stereo effect):
	//
	//   x'' = x' - (popout_bias * raw_separation)
	//
	// Then we rearrange the nvidia formula and substitute in the two
	// previous formulas to find the new convergence:
	//
	//   x'' = separation * (depth - convergence') / depth
	//   convergence' = depth * (1 - (x'' / separation))
	//   convergence' = depth * (((popout_bias * raw_separation) - x') / separation + 1)
	//   convergence' = depth * popout * raw_separation / separation + convergence
	//
	float new_convergence = w * popout * raw_sep / separation + target_convergence;

	// Apply the minimum convergence now to ensure we can't go negative
	// regardless of what the popout bias did, and a hard maximum
	// convergence to prevent us going near infinity:
	new_convergence = min(max(new_convergence, min_convergence), max_convergence_hard);

	if (any(abs(new_convergence - state[0].last_convergence.xyzw) < anti_judder_threshold)) {
		// FIXME: This just prevents the change, but that might
		// sometimes leave it with something obscuring the camera. We
		// might be better selecting the minimum convergence, but have
		// to be careful that doesn't cause us other problems.
		auto_convergence = 1.#SNAN;
		return;
	}

	// The *2 here is to compensate for the lag in setting the
	// convergence due to the asynchronous transfer.
	float diff = slow_convergence_rate * (time - prev_time) * 2;

	convergence_difference = new_convergence - current_convergence;
	if (abs(convergence_difference) >= instant_convergence_threshold) {
		auto_convergence = new_convergence;
	} else if (-convergence_difference > slow_convergence_threshold_near) {
		auto_convergence = max(new_convergence, current_convergence - diff);
	} else if (convergence_difference > slow_convergence_threshold_far) {
		auto_convergence = min(new_convergence, current_convergence + diff);
	} else {
		auto_convergence = 1.#QNAN;
	}

	state[0].last_convergence.xyzw = float4(current_convergence, state[0].last_convergence.xyz);
}
