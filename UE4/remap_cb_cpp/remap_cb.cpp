#include <string>
#include <unordered_map>
#include <fstream>
#include <stdio.h>

#define LogInfo printf
#define D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT 14

static bool patch_cb(std::string *asm_text, unsigned cb_reg, size_t *dcl_end, unsigned *tmp_regs, unsigned shader_model_major)
{
	std::unordered_map<unsigned, unsigned> cb_idx_to_tmp_reg;
	std::unordered_map<unsigned, unsigned>::iterator i;
	std::string cb_search, cb_index_str, tmp_reg_str, insert_str;
	size_t cb_pos, cb_idx_start, cb_idx_end;
	bool patched = false;
	unsigned cb_idx, tmp_reg;
	unsigned ld_idx, ld_off;

	cb_search = std::string("cb") + std::to_string(cb_reg) + std::string("[");
	LogInfo("Redirecting cb%d to t%d\n", cb_reg, cb_reg + 100);

	for (
		cb_pos = asm_text->find(cb_search, *dcl_end);
		cb_pos != std::string::npos;
		cb_pos = asm_text->find(cb_search, cb_pos + 1)
	) {
		cb_idx_start = cb_pos + cb_search.length();
		cb_idx_end = asm_text->find("]", cb_idx_start);
		cb_index_str = asm_text->substr(cb_idx_start, cb_idx_end - cb_idx_start);
		if (cb_index_str[0] < '0' || cb_index_str[0] > '9') {
			LogInfo("Cannot patch cb[%s]\n", cb_index_str.c_str()); // yet ;-)
			continue;
		}
		cb_idx = stoul(asm_text->substr(cb_idx_start, 4));

		try {
			tmp_reg = cb_idx_to_tmp_reg.at(cb_idx);
		} catch (std::out_of_range) {
			tmp_reg = (*tmp_regs)++;
			cb_idx_to_tmp_reg[cb_idx] = tmp_reg;
		}

		tmp_reg_str = std::string("r") + std::to_string(tmp_reg);
		LogInfo("Replacing cb%d[%s] with %s\n", cb_reg, cb_index_str.c_str(), tmp_reg_str.c_str());
		asm_text->replace(cb_pos, cb_idx_end - cb_pos + 1, tmp_reg_str);

		patched = true;
	}

	if (!patched)
		return false;

	insert_str = std::string("\ndcl_resource_structured t")
		+ std::to_string(cb_reg + 100)
		+ std::string(", 2048"); // Max allowed stride
	LogInfo("Inserting %s\n", insert_str.substr(1).c_str());
	asm_text->insert(*dcl_end, insert_str);
	*dcl_end += insert_str.length();

	for (i = cb_idx_to_tmp_reg.begin(); i != cb_idx_to_tmp_reg.end(); i++) {
		cb_idx = i->first * 16;
		tmp_reg = i->second;
		ld_idx = cb_idx / 2048;
		ld_off = cb_idx % 2048;

		if (shader_model_major == 5) {
			insert_str = std::string("\nld_structured_indexable(structured_buffer, stride=2048)(mixed,mixed,mixed,mixed) r");
		} else {
			insert_str = std::string("\nld_structured r");
			"ld_structured {reg}.xyzw, l({idx}), l({offset}), t{sb}.xyzw";
		}
		insert_str = insert_str
			+ std::to_string(tmp_reg)
			+ std::string(".xyzw, l(")
			+ std::to_string(ld_idx)
			+ std::string("), l(")
			+ std::to_string(ld_off)
			+ std::string("), t")
			+ std::to_string(cb_reg + 100)
			+ std::string(".xyzw");

		LogInfo("Inserting %s\n", insert_str.substr(1).c_str());
		asm_text->insert(*dcl_end, insert_str);
	}

	return true;
}

static bool patch_ue4_asm_text(std::string *asm_text,
		bool patch_cbuffers[D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT],
		int disable_driver_stereo_vs_reg, int disable_driver_stereo_ds_reg)
{
	bool patched = false;
	size_t dcl_start, dcl_end, dcl_temps, dcl_temps_end;
	size_t dcl_cb, shader_model_pos;
	std::string shader_model;
	unsigned shader_model_major, tmp_regs = 0, cb_reg;
	std::string insert_str;
	int disable_driver_stereo_reg = -1;

	for (
		shader_model_pos = asm_text->find("\n");
		shader_model_pos != std::string::npos && (*asm_text)[shader_model_pos + 1] == '/';
		shader_model_pos = asm_text->find("\n", shader_model_pos + 1)
	) {}
	shader_model = asm_text->substr(shader_model_pos + 1, asm_text->find("\n", shader_model_pos + 1) - shader_model_pos - 1);
	shader_model_major = stoul(asm_text->substr(shader_model_pos + 4, 1));
	LogInfo("Found %s\n", shader_model.c_str());
	if (shader_model_major < 4 || shader_model_major > 5) {
		LogInfo("Unsupported shader model\n");
		return false;
	}

	if (shader_model[0] == 'v')
		disable_driver_stereo_reg = disable_driver_stereo_vs_reg;
	else if (shader_model[0] == 'd')
		disable_driver_stereo_reg = disable_driver_stereo_ds_reg;

	dcl_start = asm_text->find("\ndcl_", shader_model_pos);
	dcl_end = asm_text->rfind("\ndcl_");
	dcl_end = asm_text->find("\n", dcl_end + 1);
	dcl_temps = asm_text->find("\ndcl_temps ", dcl_start);

	if (dcl_temps != std::string::npos) {
		tmp_regs = stoul(asm_text->substr(dcl_temps + 10, 4));
		LogInfo("Found dcl_temps %d\n", tmp_regs);
	}

	for (
		dcl_cb = asm_text->find("dcl_constantbuffer ", dcl_start);
		dcl_cb != std::string::npos;
		dcl_cb = asm_text->find("dcl_constantbuffer ", dcl_cb + 1)
	) {
		cb_reg = stoul(asm_text->substr(dcl_cb + 21, 2));
		LogInfo("Found dcl_constantbuffer cb%d\n", cb_reg);

		if (cb_reg == disable_driver_stereo_reg) {
			LogInfo("!!! WARNING: cb%d conflicts with driver stereo reg - SHADER BROKEN !!!\n", cb_reg);
			// TODO: BeepFailure();
			disable_driver_stereo_reg = -1;
		}

		// There are two constant buffers reserved for system use. They
		// can't be used in HLSL, but could potentially be used in
		// assembly, so we need to check that we are in the expected
		// range before using it to index into patch_cbuffers:
		if (cb_reg >= D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT) {
			LogInfo("cb%d out of range\n", cb_reg);
			continue;
		}

		if (!patch_cbuffers[cb_reg])
			continue;

		patched = patch_cb(asm_text, cb_reg, &dcl_end, &tmp_regs, shader_model_major) || patched;
	}

	// XXX: Here or after disabling the driver stereo cb?
	if (!patched)
		return false;

	if (disable_driver_stereo_reg != -1) {
		insert_str = std::string("\ndcl_constantbuffer cb")
			+ std::to_string(disable_driver_stereo_reg)
			+ std::string("[4], immediateIndexed");
		LogInfo("Disabling driver stereo correction: %s\n", insert_str.substr(1).c_str());
		asm_text->insert(dcl_end, insert_str);
		dcl_end += insert_str.size();
	}

	if (dcl_temps != std::string::npos) {
		dcl_temps += 11;
		dcl_temps_end = asm_text->find("\n", dcl_temps);
		LogInfo("Updating dcl_temps %d\n", tmp_regs);
		asm_text->replace(dcl_temps, dcl_temps_end - dcl_temps, std::to_string(tmp_regs));
		// TODO: Fixup dcl_end
	} else {
		insert_str = std::string("\ndcl_temps ") + std::to_string(tmp_regs);
		LogInfo("Inserting dcl_temps %d\n", tmp_regs);
		asm_text->insert(dcl_end, insert_str);
		dcl_end += insert_str.size();
	}
	// NOTE: dcl_end is no longer valid

	return true;
}

int main(int argc, char *argv[])
{
	bool patch_cbuffers [D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT] = {false};
	std::string shader;
	unsigned i, j;
	bool patched;

	if (argc < 2) {
		printf("Usage: %s file.asm\n", argv[0]);
		return 1;
	}

	std::ifstream ifs(argv[1]);
	shader.assign((std::istreambuf_iterator<char>(ifs)), (std::istreambuf_iterator<char>()));

	for (i = 2; i < argc; i++) {
		j = atol(argv[i]);
		if (j >= D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT)
			return 1;
		patch_cbuffers[j] = true;
	}

	patched = patch_ue4_asm_text(&shader, patch_cbuffers, 12, 12);

	if (patched)
		printf("\nPatched shader:\n%s", shader.c_str());
	else
		printf("\nNot patching shader\n");

	return 0;
}
