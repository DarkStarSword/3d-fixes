#!/usr/bin/env python3

# Quick n dirty tool to fix precision errors in dx11 shader disassembly.
# Minimal attempt to ensure the correct floats are fixed in the original,
# so, this will produce garbage, but might still save time

import float_to_hex
import sys, struct
import argparse
from io import BytesIO

import dx11shaderanalyse

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('original', type=argparse.FileType('rb'))
	parser.add_argument('disassembled', type=argparse.FileType('rb'))
	parser.add_argument('assembly', type=argparse.FileType('rb+'), nargs='?')
	parser.add_argument('new_assembly', type=argparse.FileType('wb'), nargs='?')
	args = parser.parse_args();

	if args.assembly:
		text = args.assembly.read().decode('ascii')
		if args.new_assembly:
			args.assembly = args.new_assembly
		else:
			args.assembly.seek(0)
			args.assembly.truncate()
	else:
		text = None

	oshex = BytesIO(dx11shaderanalyse.get_chunk(args.original, b'SHEX'))
	dshex = BytesIO(dx11shaderanalyse.get_chunk(args.disassembled, b'SHEX'))

	while True:
		dbytes = dshex.read(4)
		obytes = oshex.read(4)

		if not obytes and not dbytes:
			if args.assembly:
				args.assembly.write(text.encode('ascii'))
			return

		dbytes = struct.unpack('<I', dbytes)[0]
		obytes = struct.unpack('<I', obytes)[0]

		if obytes != dbytes:
			dstr = '%f' % struct.unpack('<f', struct.pack('<I', dbytes))[0]
			bstr = float_to_hex.hex_to_best_float_str(dbytes)
			ostr = float_to_hex.hex_to_best_float_str(obytes)
			print('0x%08X:' % args.original.tell())
			print('Disassembled: 0x%08x %s %s' % (dbytes, dstr, bstr))
			print('    Original: 0x%08x %s' % (obytes, ostr))
			print()
			if text is not None:
				(before, garbage, text) = text.partition(dstr)
				args.assembly.write((before + ostr).encode('ascii'))


if __name__ == '__main__':
	main()
