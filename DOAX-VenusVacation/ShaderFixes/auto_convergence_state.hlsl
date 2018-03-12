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
#define prev_convergence IniParams[3].z
#define anti_judder_threshold IniParams[3].w
#define auto_convergence_hud_timeout IniParams[4].x
#define auto_convergence_enabled IniParams[4].y
#define warn_no_z_buffer IniParams[4].z
#define prev_stereo_active IniParams[4].w

struct auto_convergence_state {
	float4 last_convergence;
	float user_popout_bias;
	float last_adjust_time;
	bool show_hud;
	bool prev_auto_convergence_enabled;
	bool no_z_buffer;
	float last_set_convergence;
};
