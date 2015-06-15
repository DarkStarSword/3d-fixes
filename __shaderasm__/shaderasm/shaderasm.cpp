// shaderasm.cpp : Defines the entry point for the console application.
//

#include "stdafx.h"

#include <d3dx9.h>
#include <io.h>
#include <fcntl.h>

static int assemble_shader(wchar_t *filename)
{
	LPD3DXBUFFER shader;
	wchar_t fname[MAX_PATH];
	int rc;
	FILE *outfp;

	rc = D3DXAssembleShaderFromFile(filename, NULL, NULL, 0, &shader, NULL);
	if (rc != D3D_OK)
		return 1;

	_wsplitpath_s(filename, NULL, 0, NULL, 0, fname, 250, NULL, 0);
	lstrcatW(fname, L".out");

	if ((rc = _wfopen_s(&outfp, fname, L"wb")))
		return rc;

	fwrite(shader->GetBufferPointer(), 1, shader->GetBufferSize(), outfp);
	fclose(outfp);

	return 0;
}

static int assemble_stdin()
{
	LPD3DXBUFFER shader;
	char *buf = NULL;
	const int block = 4096;
	size_t size = 0;

	_setmode(_fileno(stdin), O_BINARY);
	while (!feof(stdin)) {
		buf = (char*)realloc(buf, size + block);
		if (!buf)
			return 1;
		size += fread(buf + size, 1, block, stdin);
		if (ferror(stdin))
			return 1;
	}

	D3DXAssembleShader(buf, size, NULL, NULL, 0, &shader, NULL);

	_setmode(_fileno(stdout), O_BINARY);
	fwrite(shader->GetBufferPointer(), 1, shader->GetBufferSize(), stdout);

	return 0;
}

int _tmain(int argc, _TCHAR* argv[])
{
	int i;

	if (argc == 1)
		return assemble_stdin();

	for (i = 1; i < argc; i++)
		assemble_shader(argv[i]);

	return 0;
}

