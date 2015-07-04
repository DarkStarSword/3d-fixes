#!/usr/bin/env python3

import sys, os, struct, itertools

def dump_cb(stream):
	for off in itertools.count():
		for component in 'xyzw':
			buf = stream.read(4)
			if len(buf) < 4:
				return

			val = struct.unpack('<f', buf)[0]
			print('cbX[{}].{}: {}'.format(off, component, val))

def main():
	for filename in sys.argv[1:]:
		print()
		print(filename)
		dump_cb(open(filename, 'rb'))

if __name__ == '__main__':
	main()
