#!/usr/bin/env python

# Useful for calculating depth values for helixmod.blogspot.com.au to fix
# objects/UI being rendered at the wrong depth in 3D Vision.

# Helixmod author recommends http://gregstoll.dyndns.org/~gregstoll/floattohex/
# to do these conversions, but I found that using a web interface was too
# clunky and would rather just call a program from the command line to do it.
# It is somewhat amusing to me that the author of that page created it because
# he was originally using a java applet and found that to be too heavy-weight.

# His module also seemed to be overkill to me, given that the struct module can
# do exactly the same thing in one line of python, so I wrote my own.

import struct

def _float_to_hex(val):
	return struct.unpack('I', struct.pack('f', val))[0]

def _double_to_hex(val):
	return struct.unpack('Q', struct.pack('d', val))[0]

def float_to_hex(val):
	return '0x%.8x' % _float_to_hex(val)

def double_to_hex(val):
	return '0x%.16x' % _double_to_hex(val)

def _hex_to_float(val):
	return struct.unpack('f', struct.pack('I', val))[0]

def _hex_to_double(val):
	return struct.unpack('d', struct.pack('Q', val))[0]

def hex_to_float(val):
	return _hex_to_float(int(val, 16))

def hex_to_double(val):
	return _hex_to_double(int(val, 16))

def test_precision(val, precision):
	s = '%.*f' % (precision, val)
	return (float(s) == val, s)

def best_precision(val, ):
	for precision in range(50):
		print(test_precision(val, precision))
	return '%.*f' % (2, val)

def _hex_to_best_str(val, hex_to, to_hex):
	'''
	Find the smallest precision that will parse back to the original value, prefers to a
	without using scientific notation.
	'''
	f = hex_to(val)
	# There's probably some field of maths dedicated to finding and proving
	# the correct number to use here...
	for precision in range(32):
		string = '%.*f' % (precision, f)
		redecoded = to_hex(float(string))
		if val == redecoded:
			return string
	# Fine, just use scientific notation
	return str(f)

def hex_to_best_float_str(val):
	return _hex_to_best_str(val, _hex_to_float, _float_to_hex)

def hex_to_best_double_str(val):
	return _hex_to_best_str(val, _hex_to_double, _double_to_hex)

def process_vals(vals):
	yield ('from', 'float', 'double')
	yield ('----', '-----', '------')
	for val_str in vals:
		if val_str.startswith('0x'):
			val = int(val_str, 16)
			f = 'N/A'
			if (val & 0xffffffff) == val:
				f = hex_to_best_float_str(val)
			yield (val_str, f, hex_to_best_double_str(val))
		else:
			val = float(val_str)
			yield (val_str, float_to_hex(val), double_to_hex(val))

def align_output(input):
	lengths = [ map(len, x) for x in input ]
	lengths = map(max, zip(*lengths))
	format = '   '.join([ '%%%is' % l for l in lengths ])
	return '\n'.join([format % line for line in input])

def main():
	import sys
	if len(sys.argv) == 1:
		print 'usage: %s {float | hex}...' % sys.argv[0]
		sys.exit(1)

	print align_output(list(process_vals(sys.argv[1:])))

if __name__ == '__main__':
	main()
