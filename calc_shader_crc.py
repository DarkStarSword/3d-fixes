#!/usr/bin/env python3

import sys

from extract_unity_shaders import calc_shader_crc

def main():
	for filename in sys.argv[1:]:
		asm = open(filename, 'r', encoding='ascii').read()
		crc = calc_shader_crc(asm)
		print('%.8X - %s' % (crc, filename))

if __name__ == '__main__':
	main()
