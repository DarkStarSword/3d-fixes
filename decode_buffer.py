#!/usr/bin/env python3

import sys, os, struct, itertools

try:
	import float_to_hex
except ImportError:
	float_to_hex = None

def dump(stream):
	for off in itertools.count():
		buf = stream.read(4)
		if len(buf) == 0:
			return
		if len(buf) < 4: 
			print('Remaining:', repr(buf))
			return

		if float_to_hex is not None:
			fval, = struct.unpack('<I', buf)
			fval = float_to_hex.hex_to_best_float_str(fval)
		else:
			fval, = struct.unpack('<f', buf)

		ival, = struct.unpack('<i', buf)
		uval, = struct.unpack('<I', buf)

		print('{:08x}: 0x{:08x} | {: 12d} | {}'.format(off*4, uval, ival, fval))

def main():
	for filename in sys.argv[1:]:
		print()
		print(filename)
		dump(open(filename, 'rb'))

if __name__ == '__main__':
	main()
