#!/usr/bin/env python3

# Most of this code is from the imag.py module in my miasmata-fixes repository.
# The original has a full S3 decompressor and can export PNG files, which I've
# removed from this version. I'll probably add it back in at some point and add
# support for non-compressed DDS files, which would be useful to convert DDS
# files dumped with Helix mod, but right now all I want is to pull out info
# from the header to match surface properties.

import sys
import struct

# Documentation:
# https://en.wikipedia.org/wiki/S3_Texture_Compression
# http://msdn.microsoft.com/en-us/library/windows/desktop/bb943991(v=vs.85).aspx

class DDSPixelFormat(object):
	# http://msdn.microsoft.com/en-us/library/windows/desktop/bb943984(v=vs.85).aspx
	class Flags(object):
		ALPHAPIXELS = 0x00001
		ALPHA       = 0x00002
		FOURCC      = 0x00004
		RGB         = 0x00040
		YUV         = 0x00200
		LUMINANCE   = 0x20000

	def __init__(self, fp):
		(
			size,
			self.flags,
			four_cc,
			rgb_bit_count,
			r_bit_mask,
			g_bit_mask,
			b_bit_mask,
			a_bit_mask
		) = struct.unpack('<2I 4s 5I', fp.read(32))

		assert(size == 32)
		if self.flags & self.Flags.ALPHAPIXELS: # uncompressed
			self.a_bit_mask = a_bit_mask
		assert(not self.flags & self.Flags.ALPHA) # old file
		if self.flags & self.Flags.FOURCC:
			self.four_cc = four_cc
		if self.flags & self.Flags.RGB: # uncompressed
			self.rgb_bit_count = rgb_bit_count
			self.r_bit_mask = r_bit_mask
			self.g_bit_mask = g_bit_mask
			self.b_bit_mask = b_bit_mask
		assert(not self.flags & self.Flags.YUV) # old file
		assert(not self.flags & self.Flags.LUMINANCE) # old file


	def __str__(self):
		ret = []
		ret.append('Pixel Format Flags: 0x%x' % self.flags)
		if self.flags & self.Flags.ALPHAPIXELS:
			ret.append('Alpha Bit Mask: 0x%x' % self.a_bit_mask)
		if self.flags & self.Flags.FOURCC:
			ret.append('FourCC: 0x%.2x%.2x%.2x%.2x %i "%s"' % ((tuple(self.four_cc)) + (struct.unpack('<I', self.four_cc)[0], self.four_cc.decode('ascii'),)) )
		if self.flags & self.Flags.RGB:
			ret.append('RGB Bit Count: %i' % self.rgb_bit_count)
			ret.append('Red Bit Mask: 0x%x' % self.r_bit_mask)
			ret.append('Green Bit Mask: 0x%x' % self.g_bit_mask)
			ret.append('Blue Bit Mask: 0x%x' % self.b_bit_mask)
		return '\n'.join(ret)

class DDSHeader(object):
	# http://msdn.microsoft.com/en-us/library/windows/desktop/bb943982(v=vs.85).aspx
	class Flags(object):
		# Note: Don't rely on these flags - not all writers set them
		CAPS        = 0x000001
		HEIGHT      = 0x000002
		WIDTH       = 0x000004
		PITCH       = 0x000008
		PIXELFORMAT = 0x001000
		MIPMAPCOUNT = 0x020000
		LINEARSIZE  = 0x080000
		DEPTH       = 0x800000
		REQUIRED = CAPS | HEIGHT | WIDTH | PIXELFORMAT

	def __init__(self, fp):
		if fp.read(4) != b'DDS ':
			raise ValueError('Not a DDS file')
		(
			size,
			self.flags,
			self.height,
			self.width,
			self.pitch_or_linear_size,
			self.depth,
			self.mip_map_count
		) = struct.unpack('<7I 44x', fp.read(72))
		self.pixel_format = DDSPixelFormat(fp)
		(
			self.caps,
			self.caps2,
			self.caps3,
			self.caps4
		) = struct.unpack('<4I4x', fp.read(20))
		assert(size==124)
		assert(self.flags & self.Flags.REQUIRED == self.Flags.REQUIRED)

	def __str__(self):
		ret = []
		ret.append('Flags: 0x%x' % self.flags)
		ret.append('Width: %i' % self.width)
		ret.append('Height: %i' % self.height)
		ret.append('Pitch / Linear Size: %i' % self.pitch_or_linear_size)
		ret.append('Depth: %i' % self.depth)

		ret.append('Caps1: 0x%x' % self.caps)
		ret.append('Caps2: 0x%x' % self.caps2)
		ret.append('Caps3: 0x%x' % self.caps3)
		ret.append('Caps4: 0x%x' % self.caps4)

		return '%s\n\n%s' % ('\n'.join(ret), str(self.pixel_format))

if __name__ == '__main__':
	for file in sys.argv[1:]:
		header = DDSHeader(open(file, 'rb'))
		print(header)

# vi:noexpandtab:sw=8:ts=8
