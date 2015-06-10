#!/usr/bin/env python3

'''
The encoding of the files exported from Geforce 3D Profile Manager are totally
wacko. This program cleans them up. Note that for now this process is one way.
'''

import sys, os, codecs

def process_string(string, o):
	'''
	"Strings" are just binary data embedded in the file, which disregards
	the encoding of the rest of the file and must be handled specially.
	Some of these are legitimate utf16 strings, so try that encoding first.
	If that fails, convert them to a hex string instead.
	'''
	try:
		o.write('"{}"'.format(string.decode('utf16')).encode('ascii'))
	except:
		# Requires a recent Python to use hex as a codec (or backport
		# this to Python2)... IIRC this was added in Python 3.4:
		o.write(b'0x' + codecs.encode(string, 'hex'))

def sanitise(in_filename, out_filename):
	i = open(in_filename, 'rb').read()
	o = open(out_filename, 'wb')

	assert(i[0:2] == b'\xff\xfe')
	pos = 2

	while True:
		strpos = i.find(b'"\0', pos)
		if strpos == -1:
			o.write(i[pos:].decode('utf16').encode('ascii'))
			break

		o.write(i[pos:strpos].decode('utf16').encode('ascii'))

		strendpos = i.find(b'"\0', strpos + 2)

		string = i[strpos + 2:strendpos]
		process_string(string, o)

		pos = strendpos + 2

def main():
	for file in sys.argv[1:]:
		dest = '{}-cleaned.txt'.format(file[:file.rfind('.')])
		sanitise(file, dest)

if __name__ == '__main__':
	main()
