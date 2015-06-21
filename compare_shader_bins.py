#!/usr/bin/env python3

# Quick n dirty tool to fix precision errors in dx11 shader disassembly.
# Minimal attempt to ensure the correct floats are fixed in the original,
# so, this will produce garbage, but might still save time

import float_to_hex
import sys, struct

def main():
	orig = open(sys.argv[1], 'rb')
	diss = open(sys.argv[2], 'rb')
	try:
		assembly = open(sys.argv[3], 'rb').read().decode('ascii')
		out = open(sys.argv[4], 'wb')
	except:
		assembly = None
		out = None

	# Skip checksum in header
	orig.read(0x20)
	diss.read(0x20)

	while True:
		dbytes = diss.read(4)
		obytes = orig.read(4)

		if not obytes and not dbytes:
			out.write(assembly.encode('ascii'))
			return

		dbytes = struct.unpack('<I', dbytes)[0]
		obytes = struct.unpack('<I', obytes)[0]

		if obytes != dbytes:
			dstr = '%f' % struct.unpack('<f', struct.pack('<I', dbytes))[0]
			bstr = float_to_hex.hex_to_best_float_str(dbytes)
			ostr = float_to_hex.hex_to_best_float_str(obytes)
			print('0x%08X:' % orig.tell())
			print('Disassembled: 0x%08x %s %s' % (dbytes, dstr, bstr))
			print('    Original: 0x%08x %s' % (obytes, ostr))
			print()
			if assembly is not None:
				(before, garbage, assembly) = assembly.partition(dstr)
				out.write((before + ostr).encode('ascii'))


if __name__ == '__main__':
	main()
