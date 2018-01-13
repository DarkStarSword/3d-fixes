#!/usr/bin/env python

from __future__ import print_function

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

def _hex_to_best_str(val, hex_to, to_hex):
	'''
	Find the smallest precision that will parse back to the original value, prefers to a
	without using scientific notation.
	'''
	f = hex_to(val)
	# If the value is an integer, the %f won't bound the precision, so enforce
	# a maximum value:
	if abs(f) <= 10**16:
		for precision in range(1, 16):
			string = '%.*f' % (precision, f)
			redecoded = to_hex(float(string))
			if val == redecoded:
				return string
	# Try again, but this time with scientific notation:
	for precision in range(1, 17):
		string = '%.*e' % (precision, f)
		redecoded = to_hex(float(string))
		if val == redecoded:
			return string
	# Fine, just use python's str(), which uses lots of precision by default:
	return str(f)

def hex_to_best_float_str(val):
	# After some testing, I think this will always reproduce a 32bit float
	# exactly:
	# return '%.9g' % _hex_to_float(val)

	# While this will not:
	# return '%.8g' % _hex_to_float(val)

	# And this will eliminate redundant digits for clearer results:
	return _hex_to_best_str(val, _hex_to_float, _float_to_hex)

def hex_to_best_double_str(val):

	# Need at least 16 digits of precision in scientific notation for doubles:
	# return '%.16e' % _hex_to_double(val)

	# Or 17 if using %g
	# return '%.17g' % _hex_to_double(val)

	return _hex_to_best_str(val, _hex_to_double, _double_to_hex)

def f32_sign(val):
	return (val & 0x80000000) and '-' or '+'

def f32_exponent(val):
	biased = (val & 0x7f800000) >> 23
	if biased == 0:
		return 'zero/subnorm'
	if biased == 0xff:
		return 'inf/NAN'
	return str(biased - 127)

def is_subnormal(val):
	return (val & 0x7f800000) == 0x00000000

def f32_mantissa(val):
	m = val & 0x007fffff
	if is_subnormal(val):
		return str(m / float(0x00800000))
	return str((m | 0x00800000) / float(0x00800000))

def process_vals(vals, verbose=False):
	if verbose:
		yield ('from', 'float', 'check', 'double', 'check', 'sign', 'exponent', 'mantissa')
		yield ('----', '-----', '-----', '------', '-----', '----', '--------', '--------')
	else:
		yield ('from', 'float', 'check', 'double', 'check')
		yield ('----', '-----', '-----', '------', '-----')
	for val_str in vals:
		if val_str.startswith('0x'):
			val = int(val_str, 16)
			f = fm = 'N/A'
			if (val & 0xffffffff) == val:
				f = hex_to_best_float_str(val)
				fc = float_to_hex(float(f))
				fm = int(fc,16) == int(val_str,16)
				if not fm:
					fm = '%s (%s)' % (str(fm), fc)
			d = hex_to_best_double_str(val)
			dc = double_to_hex(float(d))
			dm = int(dc,16) == int(val_str,16)
			if not dm:
					dm = '%s (%s)' % (str(dm), dc)
			if verbose:
				yield (val_str, f, str(fm), hex_to_best_double_str(val), str(dm), f32_sign(val), f32_exponent(val), f32_mantissa(val))
			else:
				yield (val_str, f, str(fm), hex_to_best_double_str(val), str(dm))
		else:
			val = float(val_str)
			f = float_to_hex(val)
			i = int(f, 16)
			fm = hex_to_best_float_str(i)
			d = double_to_hex(val)
			dm = hex_to_best_double_str(int(d, 16))
			if verbose:
				yield (val_str, f, fm, d, dm, f32_sign(i), f32_exponent(i), f32_mantissa(i))
			else:
				yield (val_str, f, fm, d, dm)

def align_output(input):
	lengths = [ map(len, x) for x in input ]
	lengths = map(max, zip(*lengths))
	format = '   '.join([ '%%%is' % l for l in lengths ])
	return '\n'.join([format % line for line in input])

def run_tests_32():
	worst_case_e0_float = '0x3f800001' # mantissa has implicit high bit and explicit low bit, unbiased exponent is 0
	worst_case_neg_e0_float = '0xbf800001' # mantissa has implicit high bit and explicit low bit, unbiased exponent is 0, sign bit set
	worst_case_normal_float = '0x00800001' # mantissa has implicit high bit and explicit low bit, unbiased exponent is -126
	worst_case_subnormal_float = '0x00000001' # mantissa has explicit low bit set, unbiased exponent is -127
	worst_case_9_precision = '0x447fffff' # 1023.99994 - example of case that requires 9 precision digits
	worst_case_random = '0x3dfb630e' # Random number found to fail with only 8 precision digits

	tests = [worst_case_e0_float, worst_case_neg_e0_float,
			worst_case_normal_float, worst_case_subnormal_float,
			worst_case_random, worst_case_9_precision]

	print(align_output(list(process_vals(tests))))

	# Try worst case scenario mantissas with all possible exponents and sign bits:
	tests = []
	for i in range(512):
		tests.append('0x%.8x' % (0x00000001 | i << 23))
		tests.append('0x%.8x' % (0x007fffff | i << 23))
	print(align_output(list(process_vals(tests))))

	tests = []
	for i in range(10000):
		import random
		# mantissa = 0x007fffff
		# exponent = 0x7f800000, 0 is special
		# sign     = 0x80000000
		f = random.randint(0, 0xffffffff)
		tests.append('0x%08x' % f)
	print(align_output(list(process_vals(tests))))

def run_tests_64():
	tests = []
	for i in range(10000):
		import random
		f = random.randint(0, 0xffffffffffffffff)
		tests.append('0x%016x' % f)
	print(align_output(list(process_vals(tests))))

def run_tests_ms_accuracy():
	def _run_tests_ms_accuracy(start = 16384, length = 100):
		for s in range(start, start + length):
			for ms in range(1000):
				dec = '%i.%03i' % (s, ms)
				f = float(dec)

				fe = struct.pack('f', f)
				f, = struct.unpack('f', fe)

				cs = int(f)
				cms = int(round(f * 1000)) % 1000
				cdec = '%i.%03i' % (cs, cms)

				if (cs != s or cms != ms):
					print('Resolution lost at %s, became %s 0x%08x' % (dec, cdec, struct.unpack('I', fe)[0]))
	x = 16384

	#_run_tests_ms_accuracy(0, x) # No resolution loss
	_run_tests_ms_accuracy(x, 10) # 4.5 hours, resolution down to 2ms
	#_run_tests_ms_accuracy(x << 1, 10) # 9 hours, resolution down to 4ms
	#_run_tests_ms_accuracy(x << 2, 10) # 18 hours, resolution down to 8ms
	#_run_tests_ms_accuracy(x << 3, 10) # 36 hours, resolution down to 16ms - on par with system timer
	#_run_tests_ms_accuracy(x << 4, 10) # 72 hours, resolution down to 31-32ms - worse than system timer
	#_run_tests_ms_accuracy(x << 5, 10) # 6 days, resolution down to 62-63ms
	#_run_tests_ms_accuracy(x << 6, 10) # 12.1 days, resolution down to 125ms
	#_run_tests_ms_accuracy(x << 7, 10) # 24.3 days, resolution down to 249-251ms
	#_run_tests_ms_accuracy(x << 8, 10) # 48.5 days, resolution down to 499ms
	# GetTickCount() wraps around at 49.7 days

def main():
	import sys
	if len(sys.argv) == 1:
		print('usage: %s {float | hex}...' % sys.argv[0])
		sys.exit(1)

	if sys.argv[1] == 'test':
		return run_tests_32()

	if sys.argv[1] == 'test64':
		return run_tests_64()

	if sys.argv[1] == 'testms':
		return run_tests_ms_accuracy()

	if sys.argv[1] == '-v':
		print(align_output(list(process_vals(sys.argv[2:], True))))
		return

	print(align_output(list(process_vals(sys.argv[1:]))))

if __name__ == '__main__':
	main()

# vi: noet ts=4:sw=4
