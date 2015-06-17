#!/usr/bin/env python3

# Most of this code is from the imag.py module in my miasmata-fixes repository.
# The original has a full S3 decompressor and can export PNG files, which I've
# removed from this version. I'll probably add it back in at some point and add
# support for non-compressed DDS files, which would be useful to convert DDS
# files dumped with Helix mod, but right now all I want is to pull out info
# from the header to match surface properties.

import sys, os
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
	113: (np.dtype([('R', '<f2'), ('G', '<f2'), ('B', '<f2'), ('A', '<f2')]), 'RGBA'), # D3DFMT_A16B16G16R16F
}

dxgi_formats = {
# https://msdn.microsoft.com/en-us/library/windows/desktop/bb173059(v=vs.85).aspx
	# FIXME: 24bit R, 8bit G... Probably need to do my own making & extraction?
	# 44: (np.dtype([('R', '<f4')]), 'RGB'), #   DXGI_FORMAT_R24G8_TYPELESS

#   DXGI_FORMAT_R32G32B32A32_TYPELESS       = 1,
#   DXGI_FORMAT_R32G32B32A32_FLOAT          = 2,
#   DXGI_FORMAT_R32G32B32A32_UINT           = 3,
#   DXGI_FORMAT_R32G32B32A32_SINT           = 4,
#   DXGI_FORMAT_R32G32B32_TYPELESS          = 5,
#   DXGI_FORMAT_R32G32B32_FLOAT             = 6,
#   DXGI_FORMAT_R32G32B32_UINT              = 7,
#   DXGI_FORMAT_R32G32B32_SINT              = 8,
#   DXGI_FORMAT_R16G16B16A16_TYPELESS       = 9,
#   DXGI_FORMAT_R16G16B16A16_FLOAT          = 10,
#   DXGI_FORMAT_R16G16B16A16_UNORM          = 11,
#   DXGI_FORMAT_R16G16B16A16_UINT           = 12,
#   DXGI_FORMAT_R16G16B16A16_SNORM          = 13,
#   DXGI_FORMAT_R16G16B16A16_SINT           = 14,
#   DXGI_FORMAT_R32G32_TYPELESS             = 15,
#   DXGI_FORMAT_R32G32_FLOAT                = 16,
#   DXGI_FORMAT_R32G32_UINT                 = 17,
#   DXGI_FORMAT_R32G32_SINT                 = 18,
#   DXGI_FORMAT_R32G8X24_TYPELESS           = 19,
#   DXGI_FORMAT_D32_FLOAT_S8X24_UINT        = 20,
#   DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS    = 21,
#   DXGI_FORMAT_X32_TYPELESS_G8X24_UINT     = 22,
#   DXGI_FORMAT_R10G10B10A2_TYPELESS        = 23,
#   DXGI_FORMAT_R10G10B10A2_UNORM           = 24,
#   DXGI_FORMAT_R10G10B10A2_UINT            = 25,
#   DXGI_FORMAT_R11G11B10_FLOAT             = 26,
#   DXGI_FORMAT_R8G8B8A8_TYPELESS           = 27,
#   DXGI_FORMAT_R8G8B8A8_UNORM              = 28,
#   DXGI_FORMAT_R8G8B8A8_UNORM_SRGB         = 29,
#   DXGI_FORMAT_R8G8B8A8_UINT               = 30,
#   DXGI_FORMAT_R8G8B8A8_SNORM              = 31,
#   DXGI_FORMAT_R8G8B8A8_SINT               = 32,
#   DXGI_FORMAT_R16G16_TYPELESS             = 33,
#   DXGI_FORMAT_R16G16_FLOAT                = 34,
#   DXGI_FORMAT_R16G16_UNORM                = 35,
#   DXGI_FORMAT_R16G16_UINT                 = 36,
#   DXGI_FORMAT_R16G16_SNORM                = 37,
#   DXGI_FORMAT_R16G16_SINT                 = 38,
#   DXGI_FORMAT_R32_TYPELESS                = 39,
#   DXGI_FORMAT_D32_FLOAT                   = 40,
#   DXGI_FORMAT_R32_FLOAT                   = 41,
#   DXGI_FORMAT_R32_UINT                    = 42,
#   DXGI_FORMAT_R32_SINT                    = 43,
#   DXGI_FORMAT_D24_UNORM_S8_UINT           = 45,
#   DXGI_FORMAT_R24_UNORM_X8_TYPELESS       = 46,
#   DXGI_FORMAT_X24_TYPELESS_G8_UINT        = 47,
#   DXGI_FORMAT_R8G8_TYPELESS               = 48,
#   DXGI_FORMAT_R8G8_UNORM                  = 49,
#   DXGI_FORMAT_R8G8_UINT                   = 50,
#   DXGI_FORMAT_R8G8_SNORM                  = 51,
#   DXGI_FORMAT_R8G8_SINT                   = 52,
#   DXGI_FORMAT_R16_TYPELESS                = 53,
#   DXGI_FORMAT_R16_FLOAT                   = 54,
#   DXGI_FORMAT_D16_UNORM                   = 55,
#   DXGI_FORMAT_R16_UNORM                   = 56,
#   DXGI_FORMAT_R16_UINT                    = 57,
#   DXGI_FORMAT_R16_SNORM                   = 58,
#   DXGI_FORMAT_R16_SINT                    = 59,
#   DXGI_FORMAT_R8_TYPELESS                 = 60,
#   DXGI_FORMAT_R8_UNORM                    = 61,
#   DXGI_FORMAT_R8_UINT                     = 62,
#   DXGI_FORMAT_R8_SNORM                    = 63,
#   DXGI_FORMAT_R8_SINT                     = 64,
#   DXGI_FORMAT_A8_UNORM                    = 65,
#   DXGI_FORMAT_R1_UNORM                    = 66,
#   DXGI_FORMAT_R9G9B9E5_SHAREDEXP          = 67,
#   DXGI_FORMAT_R8G8_B8G8_UNORM             = 68,
#   DXGI_FORMAT_G8R8_G8B8_UNORM             = 69,
#   DXGI_FORMAT_BC1_TYPELESS                = 70,
#   DXGI_FORMAT_BC1_UNORM                   = 71,
#   DXGI_FORMAT_BC1_UNORM_SRGB              = 72,
#   DXGI_FORMAT_BC2_TYPELESS                = 73,
#   DXGI_FORMAT_BC2_UNORM                   = 74,
#   DXGI_FORMAT_BC2_UNORM_SRGB              = 75,
#   DXGI_FORMAT_BC3_TYPELESS                = 76,
#   DXGI_FORMAT_BC3_UNORM                   = 77,
#   DXGI_FORMAT_BC3_UNORM_SRGB              = 78,
#   DXGI_FORMAT_BC4_TYPELESS                = 79,
#   DXGI_FORMAT_BC4_UNORM                   = 80,
#   DXGI_FORMAT_BC4_SNORM                   = 81,
#   DXGI_FORMAT_BC5_TYPELESS                = 82,
#   DXGI_FORMAT_BC5_UNORM                   = 83,
#   DXGI_FORMAT_BC5_SNORM                   = 84,
#   DXGI_FORMAT_B5G6R5_UNORM                = 85,
#   DXGI_FORMAT_B5G5R5A1_UNORM              = 86,
#   DXGI_FORMAT_B8G8R8A8_UNORM              = 87,
#   DXGI_FORMAT_B8G8R8X8_UNORM              = 88,
#   DXGI_FORMAT_R10G10B10_XR_BIAS_A2_UNORM  = 89,
#   DXGI_FORMAT_B8G8R8A8_TYPELESS           = 90,
#   DXGI_FORMAT_B8G8R8A8_UNORM_SRGB         = 91,
#   DXGI_FORMAT_B8G8R8X8_TYPELESS           = 92,
#   DXGI_FORMAT_B8G8R8X8_UNORM_SRGB         = 93,
#   DXGI_FORMAT_BC6H_TYPELESS               = 94,
#   DXGI_FORMAT_BC6H_UF16                   = 95,
#   DXGI_FORMAT_BC6H_SF16                   = 96,
#   DXGI_FORMAT_BC7_TYPELESS                = 97,
#   DXGI_FORMAT_BC7_UNORM                   = 98,
#   DXGI_FORMAT_BC7_UNORM_SRGB              = 99,
#   DXGI_FORMAT_AYUV                        = 100,
#   DXGI_FORMAT_Y410                        = 101,
#   DXGI_FORMAT_Y416                        = 102,
#   DXGI_FORMAT_NV12                        = 103,
#   DXGI_FORMAT_P010                        = 104,
#   DXGI_FORMAT_P016                        = 105,
#   DXGI_FORMAT_420_OPAQUE                  = 106,
#   DXGI_FORMAT_YUY2                        = 107,
#   DXGI_FORMAT_Y210                        = 108,
#   DXGI_FORMAT_Y216                        = 109,
#   DXGI_FORMAT_NV11                        = 110,
#   DXGI_FORMAT_AI44                        = 111,
#   DXGI_FORMAT_IA44                        = 112,
#   DXGI_FORMAT_P8                          = 113,
#   DXGI_FORMAT_A8P8                        = 114,
#   DXGI_FORMAT_B4G4R4A4_UNORM              = 115,
#   DXGI_FORMAT_P208                        = 130,
#   DXGI_FORMAT_V208                        = 131,
#   DXGI_FORMAT_V408                        = 132,
#   DXGI_FORMAT_ASTC_4X4_UNORM              = 134,
#   DXGI_FORMAT_ASTC_4X4_UNORM_SRGB         = 135,
#   DXGI_FORMAT_ASTC_5X4_TYPELESS           = 137,
#   DXGI_FORMAT_ASTC_5X4_UNORM              = 138,
#   DXGI_FORMAT_ASTC_5X4_UNORM_SRGB         = 139,
#   DXGI_FORMAT_ASTC_5X5_TYPELESS           = 141,
#   DXGI_FORMAT_ASTC_5X5_UNORM              = 142,
#   DXGI_FORMAT_ASTC_5X5_UNORM_SRGB         = 143,
#   DXGI_FORMAT_ASTC_6X5_TYPELESS           = 145,
#   DXGI_FORMAT_ASTC_6X5_UNORM              = 146,
#   DXGI_FORMAT_ASTC_6X5_UNORM_SRGB         = 147,
#   DXGI_FORMAT_ASTC_6X6_TYPELESS           = 149,
#   DXGI_FORMAT_ASTC_6X6_UNORM              = 150,
#   DXGI_FORMAT_ASTC_6X6_UNORM_SRGB         = 151,
#   DXGI_FORMAT_ASTC_8X5_TYPELESS           = 153,
#   DXGI_FORMAT_ASTC_8X5_UNORM              = 154,
#   DXGI_FORMAT_ASTC_8X5_UNORM_SRGB         = 155,
#   DXGI_FORMAT_ASTC_8X6_TYPELESS           = 157,
#   DXGI_FORMAT_ASTC_8X6_UNORM              = 158,
#   DXGI_FORMAT_ASTC_8X6_UNORM_SRGB         = 159,
#   DXGI_FORMAT_ASTC_8X8_TYPELESS           = 161,
#   DXGI_FORMAT_ASTC_8X8_UNORM              = 162,
#   DXGI_FORMAT_ASTC_8X8_UNORM_SRGB         = 163,
#   DXGI_FORMAT_ASTC_10X5_TYPELESS          = 165,
#   DXGI_FORMAT_ASTC_10X5_UNORM             = 166,
#   DXGI_FORMAT_ASTC_10X5_UNORM_SRGB        = 167,
#   DXGI_FORMAT_ASTC_10X6_TYPELESS          = 169,
#   DXGI_FORMAT_ASTC_10X6_UNORM             = 170,
#   DXGI_FORMAT_ASTC_10X6_UNORM_SRGB        = 171,
#   DXGI_FORMAT_ASTC_10X8_TYPELESS          = 173,
#   DXGI_FORMAT_ASTC_10X8_UNORM             = 174,
#   DXGI_FORMAT_ASTC_10X8_UNORM_SRGB        = 175,
#   DXGI_FORMAT_ASTC_10X10_TYPELESS         = 177,
#   DXGI_FORMAT_ASTC_10X10_UNORM            = 178,
#   DXGI_FORMAT_ASTC_10X10_UNORM_SRGB       = 179,
#   DXGI_FORMAT_ASTC_12X10_TYPELESS         = 181,
#   DXGI_FORMAT_ASTC_12X10_UNORM            = 182,
#   DXGI_FORMAT_ASTC_12X10_UNORM_SRGB       = 183,
#   DXGI_FORMAT_ASTC_12X12_TYPELESS         = 185,
#   DXGI_FORMAT_ASTC_12X12_UNORM            = 186,
#   DXGI_FORMAT_ASTC_12X12_UNORM_SRGB       = 187,
#   DXGI_FORMAT_FORCE_UINT                  = 0xffffffff
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
	''' Convert a single channel image into a multichannel rainbow image '''
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

def parse_args():
	import argparse
	parser = argparse.ArgumentParser(description = 'DDS info & conversion script')
	parser.add_argument('files', nargs='+',
			help='List of DDS files to process')
	parser.add_argument('--convert', action='store_true',
			help='Convert supported DDS files to PNG')
	return parser.parse_args()

def convert(fp, header, dtype):
	(np_dtype, img_type) = dtype

	buf = np.fromfile(fp, np_dtype, count=header.width * header.height)
	out = Image.new(img_type, (header.width, header.height))
	pixels = out.load()

	# TODO
	# # FIXME: This will be *slow*, use numpy methods to speed this up:
	# for y in range(header.height):
	# 	for x in range(header.width):
	# 		px = buf[y * header.width + x]
	# 		if px[0]:
	# 			print(px * 3)
	# 		# pixels[x, y] = int(val * 8) # FIXME: Hardcoded scaling
	# 		# pixels[x, y] = val_to_rainbow(val, 0.0, 32.0) # FIXME: Hardcoded scaling
	# 		# pixels[x, y] = val_to_rainbow(scale_pixel(val), 0.0, scale_pixel(32.0)) # FIXME: Hardcoded scaling
	# 		#pixels[x, y] = int(scale_pixel(val) * (256 / scale_pixel(32.0))) # FIXME: Hardcoded scaling
	# 	print('.', end='')
	# 	sys.stdout.flush()

	# filename = '%s.png' % os.path.splitext(fp.name)[0]
	# out.save(filename)

def convert_dx10(fp, header):
	if header.dx10_header.dxgi_format not in dxgi_formats:
		return

	# TODO: arrays, etc.

	dtype = dxgi_formats[header.dx10_header.dxgi_format]

	convert(fp, header, dtype)

def convert_dx9(fp, header):
	if header.pixel_format.format not in d3d9_pixel_formats:
		return

	dtype = d3d9_pixel_formats[header.pixel_format.format]

	convert(fp, header, dtype)

def main():
	args = parse_args()

	print_line = False
	for file in args.files:
		print_line = print_line and print('\n' + '-'*79 + '\n') or True
		print(file + ':')
		fp = open(file, 'rb')
		header = DDSHeader(fp)
		print(header)

		if Image is None: # PIL not installed
			continue

		if args.convert:
			if header.dx10_header is not None:
				convert_dx10(fp, header)
			else:
				convert_dx9(fp, header)

if __name__ == '__main__':
	main()

# vi:noexpandtab:sw=8:ts=8
