#!/usr/bin/env python3

import sys, os, struct, itertools

try:
	import float_to_hex
except ImportError:
	float_to_hex = None

def dump_cb(stream):
	for off in itertools.count():
		for component in 'xyzw':
			buf = stream.read(4)
			if len(buf) < 4:
				return

			if float_to_hex is not None:
				val = struct.unpack('<I', buf)[0]
				val = float_to_hex.hex_to_best_float_str(val)
			else:
				val = struct.unpack('<f', buf)[0]
			print('cbX[{}].{}: {}'.format(off, component, val))

def main():
	for filename in sys.argv[1:]:
		print()
		print(filename)
		dump_cb(open(filename, 'rb'))

if __name__ == '__main__':
	main()
