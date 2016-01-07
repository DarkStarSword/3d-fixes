#!/usr/bin/env python3

import sys, os, struct, itertools, io
import argparse

try:
	import float_to_hex
except ImportError:
	float_to_hex = None

def dump(stream, args):
	last_non_zero = 0
	if args.truncate:
		out = io.StringIO()
	else:
		out = sys.stdout

	if args.offset:
		stream.seek(args.offset)

	for index in itertools.count():
		zero = True
		for offset in range(args.stride // 4):
			if args.length and args.length <= index * args.stride + offset * 4:
				return
			buf = stream.read(4)
			if len(buf) == 0:
				return
			if len(buf) < 4: 
				print('Remaining:', repr(buf), file=out)
				return

			if float_to_hex is not None:
				fval, = struct.unpack('<I', buf)
				fval = float_to_hex.hex_to_best_float_str(fval)
			else:
				fval, = struct.unpack('<f', buf)

			ival, = struct.unpack('<i', buf)
			uval, = struct.unpack('<I', buf)

			if uval:
				zero = False

			if args.stride == 4:
				print('{:08x}: '.format((index * args.stride + offset * 4)), end='', file=out)
			else:
				print('{}+{:04x}: '.format(index, offset * 4), end='', file=out)
			print('0x{:08x} | {: 12d} | {}'.format(uval, ival, fval), file=out)
		if args.truncate and not zero:
			print(out.getvalue(), end='')
			out.seek(0)
			out.truncate(0)
		if args.stride != 4:
			print(file=out)

def parse_offset(off):
	if off.lower().startswith('0x'):
		return int(off, 16)
	return int(off)

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('files', nargs='+', type=argparse.FileType('rb'))
	parser.add_argument('-s', '--stride', type=int, default=4)
	parser.add_argument('-t', '--truncate', action='store_true')
	parser.add_argument('-o', '--offset', type=parse_offset)
	parser.add_argument('-l', '--length', type=parse_offset)
	args = parser.parse_args()

	for file in args.files:
		print()
		print(file.name)
		dump(file, args)

if __name__ == '__main__':
	main()
