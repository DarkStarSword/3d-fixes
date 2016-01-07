#!/usr/bin/env python3

import sys, os, struct, itertools
import argparse

try:
	import float_to_hex
except ImportError:
	float_to_hex = None

def dump(stream, args):
	for index in itertools.count():
		for offset in range(args.stride // 4):
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

			if args.stride == 1:
				print('{:08x}: '.format((index * args.stride + offset) * 4), end='')
			else:
				print('{}+{:04x}: '.format(index, offset * 4), end='')
			print('0x{:08x} | {: 12d} | {}'.format(uval, ival, fval))
		if args.stride != 1:
			print()

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('files', nargs='+', type=argparse.FileType('rb'))
	parser.add_argument('-s', '--stride', type=int, default=1)
	args = parser.parse_args()

	for file in args.files:
		print()
		print(file.name)
		dump(file, args)

if __name__ == '__main__':
	main()
