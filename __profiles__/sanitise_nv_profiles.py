#!/usr/bin/env python3

'''
The encoding of the files exported from Geforce 3D Profile Manager are totally
wacko. This program cleans them up. Note that for now this process is one way.
'''

import sys, os, codecs, argparse
import io, itertools, re, struct
from xml.dom import minidom

key = codecs.decode('2f7c4f8b2024528d263c9477f37c98a5fa71b680dd3584bafdb6a61b39c4ccb07e95d9ee184b9cf52d4ed0c15517df181e0b188b8858865a1e03ed56fb16fe8a01329c8df2e84ae6908e1568e82df440379a72c7020cd1d358ea62d198362bb216d5de93f1ba74e332c49ff612fe18c0bb35799c6b7a237f2b159b42071aff69fb9cbd2397a822638f32c8e99b631cee2cd9ed8d3a359cb160ae5ef5976b9f208cf7982c4379951dcd46366cd96720ab412221e55582f52720f508073f6d69d91c4bf826036eb23f1ee6ca3d6144b092aff088cae05f5df4dfc64ca4e0cab0205dc0fadd9a348f50795a5f7c199e407071b54519b853fcdf24be221c79bf4289', 'hex')

def readlines_utf16(i):
	pos = 0
	while True:
		eol = i.find(b'\n\0', pos)
		if eol == -1:
			yield i[pos:]
			return
		yield i[pos:eol + 2]
		pos = eol + 2

def utf16(s):
	r = s.encode('utf16')
	if r[:2] == b'\xff\xfe':
		return  r[2:]
	return r

# I think I'm hitting a bug in the regexp if the string contains an extra " in the middle?
# internal_string_pattern = re.compile(
# 	utf16('SettingString ID_0x') +
# 	b'(?P<SettingID>[0-9a-fA-F\0]{16})' +
# 	utf16(' = "') +
# 	b'(?P<String>.*)' +
# 	utf16('" InternalSettingFlag=V0')
# )
# Breaking it up into two patterns solved the issue:
internal_string_pattern1 = re.compile(
	utf16('SettingString ID_0x') +
	b'(?P<SettingID>[0-9a-fA-F\0]{16})' +
	utf16(' = "')
)
internal_string_pattern2 = re.compile(
	utf16('" InternalSettingFlag=V0')
)

def xor_strings(s1, s2):
	return bytes([ c1 ^ c2 for c1, c2 in zip(s1, s2) ])

def decrypt_strings_utf16(i):
	o = io.StringIO()
	for line in readlines_utf16(i):
		match1 = internal_string_pattern1.search(line)
		match2 = internal_string_pattern2.search(line)
		if match1 and match2:
			id = int(match1.group('SettingID').decode('utf16'), 16)
			string = line[match1.end():match2.start()]
			off = (id << 1) % 256
			k = itertools.cycle(itertools.chain(key[off:], key[:off]))
			deciphered = xor_strings(string, k)
			if deciphered[-2:] == b'\0\0':
				deciphered = deciphered[:-2]
			# print('Deciphered', hex(id), repr(deciphered.decode('utf16')))
			o.write(line[:match1.end()].decode('utf16'))
			o.write(deciphered.decode('utf16'))
			o.write(line[match2.start():].decode('utf16'))
		else:
			o.write(line.decode('utf16'))

	return o.getvalue()

def decrypt_dword(id, value):
	off = (id << 1) % 256
	k, = struct.unpack('<I', ((key[off:] + key[:off])[:4]))
	# print('Deciphered', hex(id), hex(value), '->', hex(deciphered))
	return value ^ k

# I could merge this with the above if I wanted to do everything in one pass,
# but the above routine is dealing with binary data, whereas doing this later
# allows us to use the decoded strings, which is nicer. The key is used
# slightly differently here as well, so cleaner to keep it separate.
internal_dword_pattern = re.compile(r'''Setting ID_0x(?P<SettingID>[0-9a-fA-F]{8}) = 0x(?P<Value>[0-9a-fA-F]{8}) InternalSettingFlag=V0''')
def decrypt_dwords(i):
	o = io.StringIO()
	for line in i.splitlines(True):
		match = internal_dword_pattern.search(line)
		if match:
			id = int(match.group('SettingID'), 16)
			span = match.span('Value')
			value = int(line[span[0]:span[1]], 16)
			deciphered = decrypt_dword(id, value)
			o.write(line[:span[0]])
			o.write('%08x' % deciphered)
			o.write(line[span[1]:])
		else:
			o.write(line)
	return o.getvalue()

replace_map = []

def parse_custom_setting_names_xml():
	# The encoding specified in the nvidia inspector XML document is
	# bogus. It claims to be utf-16, but is actually utf-8. I haven't tried
	# checking if I am able to use a correctly encoded file with it, but in
	# order to work with the original I'll decode it myself here:
	path = os.path.join(os.path.dirname(sys.argv[0]), '..', 'CustomSettingNames_en-EN.xml')
	xml = open(path, 'rb').read().decode('utf-8')
	dom = minidom.parseString(xml)
	# print('\n'.join(dir(dom)))
	for CustomSetting in dom.getElementsByTagName('CustomSetting'):
		nodes = CustomSetting.getElementsByTagName('HexSettingID')
		assert(len(nodes) == 1)
		assert(len(nodes[0].childNodes) == 1)
		HexSettingID = 'ID_' + nodes[0].childNodes[0].data.lower()

		# I've never understood why XML parsing libraries all lack this basic functionality:
		nodes = [ x for x in CustomSetting.childNodes if x.nodeName == 'UserfriendlyName' ]
		assert(len(nodes) == 1)
		assert(len(nodes[0].childNodes) == 1)
		UserfriendlyName = nodes[0].childNodes[0].data

		replace_map.append((HexSettingID, '{} ({})'.format(HexSettingID, UserfriendlyName)))

def make_ids_friendly(data):
	for (id, name) in replace_map:
		data = data.replace(id, name)
	return data

def sort_settings(profile):
	# FIXME: This is pretty rigid at the moment. Tries to preserve first
	# and last couple of lines to get Profile, EndProfile, ShowOn and
	# ProfileType. Might be better to just sort settings and executables?
	lines = profile.split('\r\n')
	start = '\r\n'.join(lines[:4]) + '\r\n'
	middle = lines[4:-2]
	end = '\r\n'.join(lines[-2:])
	if middle:
		end = '\r\n' + end
	return start + '\r\n'.join(sorted(middle)) + end

def sort_profiles(data):
	# XXX: Assumes windows style newlines
	profiles = []
	buf = []
	pos = first = data.find('\r\n\r\n')
	while True:
		start = data.find('\r\nProfile', pos)
		if start == -1:
			break
		end = data.find('\r\nEndProfile', start + 1) + 14
		profiles.append(sort_settings(data[start:end]))
		pos = end
	return data[:first] + ''.join(sorted(profiles))

def parse_args():
	global args
	parser = argparse.ArgumentParser()
	parser.add_argument('files', nargs='*',
			help='NVIDIA profile text files to process')
	parser.add_argument('-d', nargs=2,
			help='Decrypt a specific DWORD setting')
	parser.add_argument('-u', '--utf8', dest='encoding', action='store_const', const='utf8', default='utf16',
			help='Use utf8 to encode the resulting file instead of utf16')
	args = parser.parse_args()


def main():
	parse_args()
	parse_custom_setting_names_xml()
	for filename in args.files:
		dest = '{}-cleaned.txt'.format(filename[:filename.rfind('.')])
		i = open(filename, 'rb').read()

		# The encrypted strings mess up the encoding, so decrypt them first and decode as utf16:
		buf = decrypt_strings_utf16(i)
		# Now the encoding has been cleanup up we can treat it as a regular string
		buf = decrypt_dwords(buf)
		buf = make_ids_friendly(buf)
		buf = sort_profiles(buf)
		open(dest, 'wb').write(buf.encode(args.encoding))
	if args.d:
		id, val = int(args.d[0], 16), int(args.d[1], 16)
		print('0x%08x' % decrypt_dword(id, val))

if __name__ == '__main__':
	main()
