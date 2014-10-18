#!/usr/bin/env python3

import sys, os, struct
import xml.dom

# These will likely change with driver updates, you can use IDA to find the
# start of the table (locate an entry in the table then scroll up until you
# find a cross reference to the first entry in the table, check the code that
# references it to find the length of the table, then just determine what file
# offset that corresponds to. The first entry was "Time"):
table_off = 0xEC9BF0
table_len = 0x4A40

struct_fmt = '<100sII'
struct_size = struct.calcsize(struct_fmt)

def main():
	f = open("c:\\windows\\SysWOW64\\nvwgf2um.dll", 'rb')
	f.seek(table_off)

	impl = xml.dom.getDOMImplementation()
	document = impl.createDocument(None, 'CustomSettingNames', None)
	xroot = document.documentElement
	xsettings = xroot.appendChild(document.createElement('Settings'))
	for i in range(0, table_len, struct_size):
		buf = f.read(struct_size)
		(name, id, unknown) = struct.unpack(struct_fmt, buf)
		name = name[:name.find(b'\0')].decode('ascii')
		# print('0x%.8x: 0x%.8x %s' % (id, unknown, name))

		xsetting = document.createElement('CustomSetting')
		xname = document.createElement('UserfriendlyName')
		xname.appendChild(document.createTextNode(name))
		xsetting.appendChild(xname)
		xid = document.createElement('HexSettingID')
		xid.appendChild(document.createTextNode('0x%.8X' % id))
		xsetting.appendChild(xid)
		xgroup = document.createElement('GroupName')
		xgroup.appendChild(document.createTextNode('Stereo'))
		xsetting.appendChild(xgroup)
		xsettings.appendChild(xsetting)

	fout = open('CustomSettingNames_en-EN.xml', 'wb')
	print('Writing CustomSettingNames_en.xml...')
	fout.write(document.toprettyxml(indent='  ', encoding='utf-16'))


if __name__ == '__main__':
	sys.exit(main())
