#!/bin/sh

if [ ! -d "$DIR" ]; then
	echo "ERROR: 3d-fixes directory not set"
	exit 1
fi

PATH="$DIR:$PATH"
DOSDIR="$DIR"
which cygpath >/dev/null 2>&1 && DOSDIR="$(cygpath -w "$DIR")"
echo "Using 3d-fixes directory: $DOSDIR"

# Check 3d-fixes contains required scripts and execute permissions are properly set:
if [ ! -x "$DIR/asmtool.py" \
  -o ! -x "$DIR/hlsltool.py" \
  -o ! -x "$DIR/shadertool.py" \
  -o ! -f "$DIR/shaderutil.py" \
  -o ! -x "$DIR/unity_asset_extractor.py" \
  -o ! -x "$DIR/unity_asset_bundle_extractor.py" \
  -o ! -x "$DIR/extract_unity55_shaders.py" \
  -o ! -x "$DIR/extract_unity53_shaders.py" \
  -o ! -x "$DIR/extract_unity_shaders.py" \
]; then
	echo "ERROR: Required scripts are missing from 3d-fixes directory."
	echo "       Please double check that you checked out / extracted 3d-fixes correctly."
	exit 1
fi

# Check python3 is installed
if ! which python3 >/dev/null 2>&1; then
	echo "ERROR: Python3 is not installed."
	echo "       Please re-run the cygwin installer and choose to install \"python3\" in the package selection."
	exit 1
fi

# Check cmd_Decompiler is installed and correct permissions. Allow either
# d3dcompiler version to be present for smoother upgrading when 3DMigoto
# switches over:
if [ ! -x "$DIR/cmd_Decompiler.exe" -o ! \( -x "$DIR/d3dcompiler_46.dll" -o -x "$DIR/d3dcompiler_47.dll" \) ]; then
	echo
	echo "ERROR: Please download the latest version of cmd_Decompiler from"
	echo "       https://github.com/bo3b/3Dmigoto/releases"
	echo "       and extract it to $DOSDIR"
	exit 1
fi

# Search for fxc:
if [ ! -x "$FXC" ]; then
	FXC=~/fxc.exe
	if [ ! -x "$FXC" ]; then
		FXC="$DIR/fxc.exe"
		if [ ! -x "$FXC" ]; then
			echo "WARNING: fxc.exe not found. HLSL shaders will not be verified"
			echo "         fxc can be found in the Windows SDK. Please copy it to $DOSDIR"
			echo -en "         Continuing without HLSL shader verification in 5...\r"
			sleep 1
			echo -en "         Continuing without HLSL shader verification in 4...\r"
			sleep 1
			echo -en "         Continuing without HLSL shader verification in 3...\r"
			sleep 1
			echo -en "         Continuing without HLSL shader verification in 2...\r"
			sleep 1
			echo -en "         Continuing without HLSL shader verification in 1...\r"
			sleep 1
			echo "         Continuing without HLSL shader verification...      "
			FXC="/bin/true"
		fi
	fi
fi
if [ "$FXC" != "/bin/true" ]; then
	DOSFXC="$FXC"
	which cygpath >/dev/null 2>&1 && DOSFXC="$(cygpath -w "$FXC")"
	echo "Using fxc: $DOSFXC"
fi
