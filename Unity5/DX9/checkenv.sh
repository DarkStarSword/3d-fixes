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
if [ ! -x "$DIR/shadertool.py" \
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
