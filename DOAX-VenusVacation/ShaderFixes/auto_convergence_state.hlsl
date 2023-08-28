#define min_convergence IniParams[1].x
#define max_convergence_soft IniParams[1].y
#define max_convergence_hard IniParams[1].z
#define ini_popout_bias IniParams[1].w
#define slow_convergence_rate IniParams[2].x
#define slow_convergence_threshold_near IniParams[2].y
#define slow_convergence_threshold_far IniParams[2].z
#define instant_convergence_threshold IniParams[2].w
#define time IniParams[3].x
#define prev_time IniParams[3].y
#define user_convergence_delta IniParams[3].z
#define anti_judder_threshold IniParams[3].w
#define prev_auto_convergence_enabled IniParams[4].x
#define auto_convergence_enabled IniParams[4].y
#define no_z_buffer IniParams[4].z
#define effective_dpi IniParams[4].w
#define resolution IniParams[5].xy

struct auto_convergence_state {
	float4 last_convergence;
	float user_popout_bias;
	float last_set_convergence;
	bool judder;
	float judder_time;
};
