#!/bin/sh -e

version="$1"

if [ -z "$version" ]; then
	echo "Specify version number"
	exit 1
fi

mkdir "$version"

cp -v "/cygdrive/c/NVIDIA/DisplayDriver/${version}/Win8_WinVista_Win7_64/International/Display.Driver/nvdrsdb.bi_" "$version/"
cp -v "/cygdrive/c/ProgramData/NVIDIA Corporation/Drs/"*.bin "$version/"
cp -v "/cygdrive/c/windows/SysWOW64/nvwgf2um.dll" "$version/"

echo Now export the profiles by hand...
./'Geforce 3D Profile Manager.exe'

echo Sanitising profiles encoding...
./sanitise_nv_profiles.py "${version}/NVIDIA Profiles.txt"
