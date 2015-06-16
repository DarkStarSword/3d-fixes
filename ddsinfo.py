#!/usr/bin/env python3

# Most of this code is from the imag.py module in my miasmata-fixes repository.
# The original has a full S3 decompressor and can export PNG files, which I've
# removed from this version. I'll probably add it back in at some point and add
# support for non-compressed DDS files, which would be useful to convert DDS
# files dumped with Helix mod, but right now all I want is to pull out info
# from the header to match surface properties.

import sys
import struct
import numpy as np
try:
	from PIL import Image
except ImportError:
	print('PIL for Python 3 not installed - will not be able to save images')
	Image = None
import math

# Documentation:
# https://en.wikipedia.org/wiki/S3_Texture_Compression
# http://msdn.microsoft.com/en-us/library/windows/desktop/bb943991(v=vs.85).aspx

d3d9_pixel_formats = {
	113: np.dtype([('R', '<f2'), ('G', '<f2'), ('B', '<f2'), ('A', '<f2')]), # D3DFMT_A16B16G16R16F
}

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

		self.format = self.four_cc = None

		assert(size == 32)
		if self.flags & self.Flags.ALPHAPIXELS: # uncompressed
			self.a_bit_mask = a_bit_mask
		assert(not self.flags & self.Flags.ALPHA) # old file
		if self.flags & self.Flags.FOURCC:
			self.four_cc = four_cc
			self.format = struct.unpack('<I', self.four_cc)[0]
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
		if self.flags & self.Flags.FOURCC:
			four_cc_str = ''.join(map(chr, filter(None, list(self.four_cc))))
			ret.append('FourCC: 0x%.2x%.2x%.2x%.2x %i "%s"' % ((tuple(self.four_cc)) + (self.format, four_cc_str,)) )
		if self.flags & self.Flags.RGB:
			ret.append('RGB Bit Count: %i' % self.rgb_bit_count)
			ret.append('  Red Bit Mask: 0x%08x' % self.r_bit_mask)
			ret.append('Green Bit Mask: 0x%08x' % self.g_bit_mask)
			ret.append(' Blue Bit Mask: 0x%08x' % self.b_bit_mask)
		if self.flags & self.Flags.ALPHAPIXELS:
			ret.append('Alpha Bit Mask: 0x%x' % self.a_bit_mask)
		return '\n'.join(ret)

class DDSHeaderDXT10(object):
	# https://msdn.microsoft.com/en-us/library/windows/desktop/bb943983(v=vs.85).aspx
	RESOURCE_DIMENSION = {
		2: 'Texture1D',
		3: 'Texture2D',
		4: 'Texture3D',
	}

	def __init__(self, fp):
		(
			self.dxgi_format,
			self.dimension,
			self.misc_flags,
			self.array_size,
			self.misc_flags2
		) = struct.unpack('<5I', fp.read(20))

	def __str__(self):
		ret = []
		ret.append('DXGI Format: %i' % self.dxgi_format)
		ret.append('Resource Dimension: %s' % self.RESOURCE_DIMENSION[self.dimension])
		ret.append('Array Size: %i' % self.array_size)
		ret.append('Misc Flags 1: 0x%x' % self.misc_flags)
		ret.append('Misc Flags 2: 0x%x' % self.misc_flags2)
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
		self.dx10_header = None
		if self.pixel_format.four_cc == b'DX10':
			self.dx10_header = DDSHeaderDXT10(fp)
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

		ret = '%s\n\n%s' % ('\n'.join(ret), str(self.pixel_format))
		if self.dx10_header is not None:
			ret += '\n\n%s' % str(self.dx10_header)
		return ret

def val_to_rainbow(val, min, max):
	segments = (
		(0, 0, 0),
		(255, 0, 0),
		(255, 255, 0),
		(0, 255, 0),
		(0, 255, 255),
		(0, 0, 255),
		(255, 0, 255),
		(255, 255, 255),
	)

	if val < min:
		return segments[0]

	def interpolate(pos, val1, val2):
		return int((1-pos) * val1 + pos * val2)

	segment_range = (max - min) / (len(segments) - 1)
	for i in range(len(segments) - 1):
		if val < segment_range * i:
			continue
		if val > segment_range * (i+1):
			continue
		pos = (val - (segment_range * i)) / segment_range
		r = interpolate(pos, segments[i][0], segments[i+1][0])
		g = interpolate(pos, segments[i][1], segments[i+1][1])
		b = interpolate(pos, segments[i][2], segments[i+1][2])
		return (r, g, b)

	return segments[-1]

def scale_pixel(val):
	return math.sqrt(val)

def parse_args():
	import argparse
	parser = argparse.ArgumentParser(description = 'DDS info & conversion script')
	parser.add_argument('files', nargs='+',
			help='List of DDS files to process')
	parser.add_argument('--convert', action='store_true',
			help='Convert supported DDS files to PNG')
	return parser.parse_args()

if __name__ == '__main__':
	args = parse_args()

	print_line = False
	for file in args.files:
		print_line = print_line and print('\n' + '-'*30 + '\n') or True
		fp = open(file, 'rb')
		header = DDSHeader(fp)
		print(header)

		if Image is None: # PIL not installed
			continue

		if args.convert and header.pixel_format.format in d3d9_pixel_formats:
			dtype = d3d9_pixel_formats[header.pixel_format.format]
			buf = np.fromfile(fp, dtype, count=header.width * header.height)

			# FIXME: Make this generic
			out = Image.new('L', (header.width, header.height))
			# out = Image.new('RGB', (header.width, header.height))
			pixels = out.load()
			# FIXME: This will be *slow*, use numpy methods to speed this up:
			for y in range(header.height):
				for x in range(header.width):
					val = float(buf[y * header.width + x]['A']) # FIXME: Hardcoded channel
					# pixels[x, y] = int(val * 8) # FIXME: Hardcoded scaling
					# pixels[x, y] = val_to_rainbow(val, 0.0, 32.0) # FIXME: Hardcoded scaling
					# pixels[x, y] = val_to_rainbow(scale_pixel(val), 0.0, scale_pixel(32.0)) # FIXME: Hardcoded scaling
					pixels[x, y] = int(scale_pixel(val) * (256 / scale_pixel(32.0))) # FIXME: Hardcoded scaling
				print('.', end='')
				sys.stdout.flush()
			out.save('sqrt.png')

# vi:noexpandtab:sw=8:ts=8
