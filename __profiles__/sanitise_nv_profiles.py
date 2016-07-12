#!/usr/bin/env python3

'''
The encoding of the files exported from Geforce 3D Profile Manager are totally
wacko. This program cleans them up. Note that for now this process is one way.
'''

import sys, os, codecs
import io
from xml.dom import minidom

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

def sanitise(in_filename, o):
	i = open(in_filename, 'rb').read()

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

def main():
	parse_custom_setting_names_xml()
	for file in sys.argv[1:]:
		dest = '{}-cleaned.txt'.format(file[:file.rfind('.')])
		stream = io.BytesIO() #FIXME: Refactor this away
		sanitise(file, stream)
		stream.seek(0)
		buf = make_ids_friendly(stream.read().decode('ascii'))
		buf = sort_profiles(buf)
		open(dest, 'wb').write(buf.encode('ascii'))

if __name__ == '__main__':
	main()
