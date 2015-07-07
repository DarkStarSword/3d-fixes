#!/usr/bin/env python3

# Most of this code is from the imag.py module in my miasmata-fixes repository.
# The original has a full S3 decompressor, which has been removed from this
# version (TODO: Add it back), but can't handle other formats that this one can.

import sys, os
import struct
import numpy as np
try:
	from PIL import Image
except ImportError:
	print('PIL for Python 3 not installed - will not be able to save images')
	Image = None
import math
import itertools
import multiprocessing

pool = None

def pr_single_threaded(*args, **kwargs):
	if multiprocessing.current_process().name == 'MainProcess':
		return print(*args, **kwargs)

# Documentation:
# https://en.wikipedia.org/wiki/S3_Texture_Compression
# http://msdn.microsoft.com/en-us/library/windows/desktop/bb943991(v=vs.85).aspx

def gamma(buf):
	return buf**(1/args.gamma)

def scale8bit(buf, bits):
	''' Returns the most significant byte only '''
	tmp = buf & (2**bits-1)
	tmp = np.float32(tmp) / (2**bits)
	tmp = gamma(tmp)
	tmp = np.clip(tmp * 255, 0, 255)
	return np.uint8(tmp)

def scale_float(buf):
	# TODO: Make clipping & scaling configurable (e.g. for HDR rendering like Witcher 3)
	if args.hdr:
		m = max(1.0, np.max(buf))
		pr_single_threaded('Scaling to', m)
		return np.uint8(np.clip(gamma(buf / m) * 255.0, 0, 255.0))
	elif args.auto_scale:
		mn = np.min(buf)
		mx = np.max(buf)
		pr_single_threaded('Scaling to {} : {}'.format(mn, mx))
		return np.uint8(np.clip(gamma((buf - mn) / (mx - mn)) * 255.0, 0, 255.0))
	else:
		return np.uint8(np.clip(gamma(buf) * 255.0, 0, 255.0))

def convert_R10G10B10A2_UINT(buf):
	r = scale8bit(buf >>  0, 10)
	g = scale8bit(buf >> 10, 10)
	b = scale8bit(buf >> 20, 10)
	a = scale8bit(buf >> 30,  2)
	return np.uint8(np.column_stack((r, g, b, a)))

def convert_R11G11B10_FLOAT(buf):
	# Extract the channels with shifts and masks, add the implicit 1 bit to
	# the mantissas and unbias the exponents:
	rm = np.int8   (((buf >>  0) & 0x3f) | 0x40)
	re = np.float16(((buf >>  6) & 0x1f)) - 15
	gm = np.int8   (((buf >> 11) & 0x3f) | 0x40)
	ge = np.float16(((buf >> 17) & 0x1f)) - 15
	bm = np.int8   (((buf >> 22) & 0x1f) | 0x20)
	be = np.float16(((buf >> 27) & 0x1f)) - 15
	# Calculate floating point values and scale:
	r = scale_float(rm * (2**re))
	g = scale_float(gm * (2**ge))
	b = scale_float(bm * (2**be))
	return np.uint8(np.column_stack((r, g, b)))

def convert_R24G8_UINT(buf):
	r = scale8bit(buf >>  0, 24)
	g = scale8bit(buf >> 24,  8)
	return np.uint8(np.column_stack((r, g, [0]*len(r))))

def convert_2x16_snorm(buf):
	# r = buf['f0'] / 0x7fff * 255
	# g = buf['f1'] / 0x7fff * 255
	# Scale to an unsigned range:
	#r = buf['f0'] / 0xffff * 255 + 0x80
	#g = buf['f1'] / 0xffff * 255 + 0x80
	# Texture I'm working on seems garbage - hard to verify this
	# r = scale8bit(buf['f0'], 16)
	# g = scale8bit(buf['f1'], 16)
	print(min(r))
	print(max(r))
	print(min(g))
	print(max(g))
	return np.uint8(np.column_stack((r, g, [0]*len(r))))

def convert_2x16f(buf):
	r = scale_float(buf['f0'])
	g = scale_float(buf['f1'])
	return np.uint8(np.column_stack((r, g, [0]*len(r))))

def convert_4x16f(buf):
	r = scale_float(buf['f0'])
	g = scale_float(buf['f1'])
	b = scale_float(buf['f2'])
	a = scale_float(buf['f3'])
	return np.uint8(np.column_stack((r, g, b, a)))

def convert_dxt5(buf, header):
	''' From my Miasmata-fixes imag.py, could probably be optimised & DXT1 support easily added back '''
	block_size = 16

	(width, height) = (header.width, header.height)

	def rgb565(c):
		r = (c & 0xf800) >> 8
		g = (c & 0x07e0) >> 3
		b = (c & 0x001f) << 3
		return np.dstack((r, g, b))

	c = [None]*4
	c[0] = buf['c0'].reshape([height / 4, width / 4])
	c[1] = buf['c1'].reshape([height / 4, width / 4])
	ct = (c[0] <= c[1]).reshape([height / 4, width / 4, 1])
	c[0] = rgb565(c[0])
	c[1] = rgb565(c[1])
	c[2] = np.choose(ct, ((2*c[0] + c[1]) / 3, (c[0] + c[1]) / 2))
	c[3] = np.choose(ct, ((c[0] + 2*c[1]) / 3, np.zeros_like(c[0])))
	del ct
	cl = buf['clookup'].reshape([height / 4, width / 4, 1]).copy()

	# Alpha:
	channels = 4
	alpha = buf['alpha'].reshape(height / 4, width / 4)
	a = [None]*8
	aa = [None]*8
	ab = [None]*8
	# Byte swapped due to reading in LE
	al = ((alpha & 0xffffffffffff0000) >> 16)
	a[0] = alpha & 0xff
	a[1] = (alpha & 0xff00) >> 8
	at = a[0] <= a[1]
	for i in range(1, 7):
		aa[i+1] = ((7-i)*a[0] + i*a[1]) / 7
	for i in range(1, 5):
		ab[i+1] = ((5-i)*a[0] + i*a[1]) / 5
	ab[6] = np.zeros_like(a[0])
	ab[7] = np.empty_like(a[0])
	ab[7].fill(255)
	for i in range(2, 8):
		a[i] = np.choose(at, [aa[i], ab[i]])
	del aa, ab, at

	out = np.empty([height, width, channels], np.uint16)
	for y in range(4):
		for x in range(4):
			# print(y, x)

			# I feel like there's probably a more efficient way to do this...

			# Look up the value
			l = np.int32(cl & 0x3)
			cl >>= 2

			# Lookup the value of each of the pixels we are working on:
			o = np.choose(l, c)
			o = np.uint16(o) # Added this when moving from miasmata-fixes to ddsinfo

			if channels == 4:
				l = np.uint8(al & 0x7)
				al >>= 3

				oa = np.choose(l, a)
				o = np.insert(o, 3, oa, 2)

			# Enlarge that 4x in both directions:
			o = o.repeat(4, 0).repeat(4, 1)

			# Construct a mask of the pixels in the final image we are working on:
			m = np.zeros([4, 4, channels], dtype=np.uint16) # Added dtype= when moving from miasmata-fixes to ddsinfo
			m[y,  x] = [1] * channels
			m = np.tile(m, [height / 4, width / 4, 1])

			# Copy these pixels to the output image - this is the slowest operation:
			np.putmask(out, m, o)

	# Finally cast to uint8 here - too early causes overflows in the DXT
	# calculations and any time after that actually slows things down
	image = Image.fromarray(np.array(out, np.uint8))

	return image

def fourcc(code):
	return struct.unpack('<I', struct.pack('4s', code.encode('ascii')))[0]

d3d9_pixel_formats = {
	# https://msdn.microsoft.com/en-us/library/windows/desktop/bb172558(v=vs.85).aspx
	# Vim Align plugin \tsq map used to align table - strings should use double quotes:
	20:             ("D3DFMT_R8G8B8",              ),
	21:             ("D3DFMT_A8R8G8B8",            ),
	22:             ("D3DFMT_X8R8G8B8",            ),
	23:             ("D3DFMT_R5G6B5",              ),
	24:             ("D3DFMT_X1R5G5B5",            ),
	25:             ("D3DFMT_A1R5G5B5",            ),
	26:             ("D3DFMT_A4R4G4B4",            ),
	27:             ("D3DFMT_R3G3B2",              ),
	28:             ("D3DFMT_A8",                  ),
	29:             ("D3DFMT_A8R3G3B2",            ),
	30:             ("D3DFMT_X4R4G4B4",            ),
	31:             ("D3DFMT_A2B10G10R10",         ),
	32:             ("D3DFMT_A8B8G8R8",            ),
	33:             ("D3DFMT_X8B8G8R8",            ),
	34:             ("D3DFMT_G16R16",              ),
	35:             ("D3DFMT_A2R10G10B10",         ),
	36:             ("D3DFMT_A16B16G16R16",        ),
	40:             ("D3DFMT_A8P8",                ),
	41:             ("D3DFMT_P8",                  ),
	50:             ("D3DFMT_L8",                  ),
	51:             ("D3DFMT_A8L8",                ),
	52:             ("D3DFMT_A4L4",                ),
	60:             ("D3DFMT_V8U8",                ),
	61:             ("D3DFMT_L6V5U5",              ),
	62:             ("D3DFMT_X8L8V8U8",            ),
	63:             ("D3DFMT_Q8W8V8U8",            ),
	64:             ("D3DFMT_V16U16",              ),
	67:             ("D3DFMT_A2W10V10U10",         ),
	70:             ("D3DFMT_D16_LOCKABLE",        ),
	71:             ("D3DFMT_D32",                 ),
	73:             ("D3DFMT_D15S1",               ),
	75:             ("D3DFMT_D24S8",               ),
	77:             ("D3DFMT_D24X8",               ),
	79:             ("D3DFMT_D24X4S4",             ),
	80:             ("D3DFMT_D16",                 ),
	82:             ("D3DFMT_D32F_LOCKABLE",       ),
	83:             ("D3DFMT_D24FS8",              ),
	84:             ("D3DFMT_D32_LOCKABLE",        ),
	85:             ("D3DFMT_S8_LOCKABLE",         ),
	81:             ("D3DFMT_L16",                 ),
	100:            ("D3DFMT_VERTEXDATA",          ),
	101:            ("D3DFMT_INDEX16",             ),
	102:            ("D3DFMT_INDEX32",             ),
	110:            ("D3DFMT_Q16W16V16U16",        ),
	111:            ("D3DFMT_R16F",                np.float16,                     "L",    scale_float),
	112:            ("D3DFMT_G16R16F",             np.dtype("<f2, <f2"),           "RGB",  convert_2x16f),
	113:            ("D3DFMT_A16B16G16R16F",       np.dtype("<f2, <f2, <f2, <f2"), "RGBA", convert_4x16f),
	114:            ("D3DFMT_R32F",                np.float32,                     "L",    scale_float),
	115:            ("D3DFMT_G32R32F",             ),
	116:            ("D3DFMT_A32B32G32R32F",       ),
	117:            ("D3DFMT_CxV8U8",              ),
	118:            ("D3DFMT_A1",                  ),
	119:            ("D3DFMT_A2B10G10R10_XR_BIAS", ),
	199:            ("D3DFMT_BINARYBUFFER",        ),
	fourcc("UYVY"): ("D3DFMT_UYVY",                ),
	fourcc("RGBG"): ("D3DFMT_R8G8_B8G8",           ),
	fourcc("YUY2"): ("D3DFMT_YUY2",                ),
	fourcc("GRGB"): ("D3DFMT_G8R8_G8B8",           ),
	fourcc("DXT1"): ("D3DFMT_DXT1",                ),
	fourcc("DXT2"): ("D3DFMT_DXT2",                ),
	fourcc("DXT3"): ("D3DFMT_DXT3",                ),
	fourcc("DXT4"): ("D3DFMT_DXT4",                ),
	fourcc("DXT5"): ("D3DFMT_DXT5",                np.dtype([('alpha', '<u8'), ('c0', '<u2'), ('c1', '<u2'), ('clookup', '<u4')]), "RGBA", convert_dxt5),
	fourcc("MET1"): ("D3DFMT_MULTI2_ARGB8",        ),
	0x7fffffff:     ("D3DFMT_FORCE_DWORD",         ),
	fourcc("DX10"): ("Refer to extended header",   ),
}

dxgi_formats = {
	# https://msdn.microsoft.com/en-us/library/windows/desktop/bb173059(v=vs.85).aspx
	# XXX: Some of the TYPELESS formats can be ambiguous as to whether they
	# should be interpreted as a float or an int. I've picked the most
	# likely option.
	# Vim Align plugin \tsq map used to align table - strings should use double quotes:
	1:          ("DXGI_FORMAT_R32G32B32A32_TYPELESS",      ),
	2:          ("DXGI_FORMAT_R32G32B32A32_FLOAT",         ),
	3:          ("DXGI_FORMAT_R32G32B32A32_UINT",          ),
	4:          ("DXGI_FORMAT_R32G32B32A32_SINT",          ),
	5:          ("DXGI_FORMAT_R32G32B32_TYPELESS",         ),
	6:          ("DXGI_FORMAT_R32G32B32_FLOAT",            ),
	7:          ("DXGI_FORMAT_R32G32B32_UINT",             ),
	8:          ("DXGI_FORMAT_R32G32B32_SINT",             ),
	9:          ("DXGI_FORMAT_R16G16B16A16_TYPELESS",      ),
	10:         ("DXGI_FORMAT_R16G16B16A16_FLOAT",         ),
	11:         ("DXGI_FORMAT_R16G16B16A16_UNORM",         ),
	12:         ("DXGI_FORMAT_R16G16B16A16_UINT",          ),
	13:         ("DXGI_FORMAT_R16G16B16A16_SNORM",         ),
	14:         ("DXGI_FORMAT_R16G16B16A16_SINT",          ),
	15:         ("DXGI_FORMAT_R32G32_TYPELESS",            ),
	16:         ("DXGI_FORMAT_R32G32_FLOAT",               ),
	17:         ("DXGI_FORMAT_R32G32_UINT",                ),
	18:         ("DXGI_FORMAT_R32G32_SINT",                ),
	19:         ("DXGI_FORMAT_R32G8X24_TYPELESS",          ),
	20:         ("DXGI_FORMAT_D32_FLOAT_S8X24_UINT",       ),
	21:         ("DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS",   ),
	22:         ("DXGI_FORMAT_X32_TYPELESS_G8X24_UINT",    ),
	23:         ("DXGI_FORMAT_R10G10B10A2_TYPELESS",       np.dtype("<u4"),            "RGBA", convert_R10G10B10A2_UINT),
	24:         ("DXGI_FORMAT_R10G10B10A2_UNORM",          ),
	25:         ("DXGI_FORMAT_R10G10B10A2_UINT",           ),
	26:         ("DXGI_FORMAT_R11G11B10_FLOAT",            np.dtype("<u4"),            "RGB",  convert_R11G11B10_FLOAT),
	27:         ("DXGI_FORMAT_R8G8B8A8_TYPELESS",          np.dtype("u1, u1, u1, u1"), "RGBA", None),
	28:         ("DXGI_FORMAT_R8G8B8A8_UNORM",             ),
	29:         ("DXGI_FORMAT_R8G8B8A8_UNORM_SRGB",        ),
	30:         ("DXGI_FORMAT_R8G8B8A8_UINT",              ),
	31:         ("DXGI_FORMAT_R8G8B8A8_SNORM",             ),
	32:         ("DXGI_FORMAT_R8G8B8A8_SINT",              ),
	33:         ("DXGI_FORMAT_R16G16_TYPELESS",            ),
	34:         ("DXGI_FORMAT_R16G16_FLOAT",               ),
	35:         ("DXGI_FORMAT_R16G16_UNORM",               ),
	36:         ("DXGI_FORMAT_R16G16_UINT",                ),
	37:         ("DXGI_FORMAT_R16G16_SNORM",               ), #np.dtype("<i2, <i2"),        "RGB", convert_2x16_snorm),
	38:         ("DXGI_FORMAT_R16G16_SINT",                ),
	39:         ("DXGI_FORMAT_R32_TYPELESS",               np.dtype("<f4"),            "L",    scale_float),
	40:         ("DXGI_FORMAT_D32_FLOAT",                  ),
	41:         ("DXGI_FORMAT_R32_FLOAT",                  ),
	42:         ("DXGI_FORMAT_R32_UINT",                   ),
	43:         ("DXGI_FORMAT_R32_SINT",                   ),
	44:         ("DXGI_FORMAT_R24G8_TYPELESS",             np.dtype("<u4"),            "RGB",  convert_R24G8_UINT),
	45:         ("DXGI_FORMAT_D24_UNORM_S8_UINT",          ),
	46:         ("DXGI_FORMAT_R24_UNORM_X8_TYPELESS",      ),
	47:         ("DXGI_FORMAT_X24_TYPELESS_G8_UINT",       ),
	48:         ("DXGI_FORMAT_R8G8_TYPELESS",              ),
	49:         ("DXGI_FORMAT_R8G8_UNORM",                 ),
	50:         ("DXGI_FORMAT_R8G8_UINT",                  ),
	51:         ("DXGI_FORMAT_R8G8_SNORM",                 ),
	52:         ("DXGI_FORMAT_R8G8_SINT",                  ),
	53:         ("DXGI_FORMAT_R16_TYPELESS",               np.dtype("<u2"),            "L",    lambda x: scale8bit(x, 16)),
	54:         ("DXGI_FORMAT_R16_FLOAT",                  ),
	55:         ("DXGI_FORMAT_D16_UNORM",                  ),
	56:         ("DXGI_FORMAT_R16_UNORM",                  ),
	57:         ("DXGI_FORMAT_R16_UINT",                   ),
	58:         ("DXGI_FORMAT_R16_SNORM",                  ),
	59:         ("DXGI_FORMAT_R16_SINT",                   ),
	60:         ("DXGI_FORMAT_R8_TYPELESS",                ),
	61:         ("DXGI_FORMAT_R8_UNORM",                   ),
	62:         ("DXGI_FORMAT_R8_UINT",                    ),
	63:         ("DXGI_FORMAT_R8_SNORM",                   ),
	64:         ("DXGI_FORMAT_R8_SINT",                    ),
	65:         ("DXGI_FORMAT_A8_UNORM",                   ),
	66:         ("DXGI_FORMAT_R1_UNORM",                   ),
	67:         ("DXGI_FORMAT_R9G9B9E5_SHAREDEXP",         ),
	68:         ("DXGI_FORMAT_R8G8_B8G8_UNORM",            ),
	69:         ("DXGI_FORMAT_G8R8_G8B8_UNORM",            ),
	70:         ("DXGI_FORMAT_BC1_TYPELESS",               ),
	71:         ("DXGI_FORMAT_BC1_UNORM",                  ),
	72:         ("DXGI_FORMAT_BC1_UNORM_SRGB",             ),
	73:         ("DXGI_FORMAT_BC2_TYPELESS",               ),
	74:         ("DXGI_FORMAT_BC2_UNORM",                  ),
	75:         ("DXGI_FORMAT_BC2_UNORM_SRGB",             ),
	76:         ("DXGI_FORMAT_BC3_TYPELESS",               ),
	77:         ("DXGI_FORMAT_BC3_UNORM",                  ),
	78:         ("DXGI_FORMAT_BC3_UNORM_SRGB",             ),
	79:         ("DXGI_FORMAT_BC4_TYPELESS",               ),
	80:         ("DXGI_FORMAT_BC4_UNORM",                  ),
	81:         ("DXGI_FORMAT_BC4_SNORM",                  ),
	82:         ("DXGI_FORMAT_BC5_TYPELESS",               ),
	83:         ("DXGI_FORMAT_BC5_UNORM",                  ),
	84:         ("DXGI_FORMAT_BC5_SNORM",                  ),
	85:         ("DXGI_FORMAT_B5G6R5_UNORM",               ),
	86:         ("DXGI_FORMAT_B5G5R5A1_UNORM",             ),
	87:         ("DXGI_FORMAT_B8G8R8A8_UNORM",             ),
	88:         ("DXGI_FORMAT_B8G8R8X8_UNORM",             ),
	89:         ("DXGI_FORMAT_R10G10B10_XR_BIAS_A2_UNORM", ),
	90:         ("DXGI_FORMAT_B8G8R8A8_TYPELESS",          ),
	91:         ("DXGI_FORMAT_B8G8R8A8_UNORM_SRGB",        ),
	92:         ("DXGI_FORMAT_B8G8R8X8_TYPELESS",          ),
	93:         ("DXGI_FORMAT_B8G8R8X8_UNORM_SRGB",        ),
	94:         ("DXGI_FORMAT_BC6H_TYPELESS",              ),
	95:         ("DXGI_FORMAT_BC6H_UF16",                  ),
	96:         ("DXGI_FORMAT_BC6H_SF16",                  ),
	97:         ("DXGI_FORMAT_BC7_TYPELESS",               ),
	98:         ("DXGI_FORMAT_BC7_UNORM",                  ),
	99:         ("DXGI_FORMAT_BC7_UNORM_SRGB",             ),
	100:        ("DXGI_FORMAT_AYUV",                       ),
	101:        ("DXGI_FORMAT_Y410",                       ),
	102:        ("DXGI_FORMAT_Y416",                       ),
	103:        ("DXGI_FORMAT_NV12",                       ),
	104:        ("DXGI_FORMAT_P010",                       ),
	105:        ("DXGI_FORMAT_P016",                       ),
	106:        ("DXGI_FORMAT_420_OPAQUE",                 ),
	107:        ("DXGI_FORMAT_YUY2",                       ),
	108:        ("DXGI_FORMAT_Y210",                       ),
	109:        ("DXGI_FORMAT_Y216",                       ),
	110:        ("DXGI_FORMAT_NV11",                       ),
	111:        ("DXGI_FORMAT_AI44",                       ),
	112:        ("DXGI_FORMAT_IA44",                       ),
	113:        ("DXGI_FORMAT_P8",                         ),
	114:        ("DXGI_FORMAT_A8P8",                       ),
	115:        ("DXGI_FORMAT_B4G4R4A4_UNORM",             ),
	130:        ("DXGI_FORMAT_P208",                       ),
	131:        ("DXGI_FORMAT_V208",                       ),
	132:        ("DXGI_FORMAT_V408",                       ),
	134:        ("DXGI_FORMAT_ASTC_4X4_UNORM",             ),
	135:        ("DXGI_FORMAT_ASTC_4X4_UNORM_SRGB",        ),
	137:        ("DXGI_FORMAT_ASTC_5X4_TYPELESS",          ),
	138:        ("DXGI_FORMAT_ASTC_5X4_UNORM",             ),
	139:        ("DXGI_FORMAT_ASTC_5X4_UNORM_SRGB",        ),
	141:        ("DXGI_FORMAT_ASTC_5X5_TYPELESS",          ),
	142:        ("DXGI_FORMAT_ASTC_5X5_UNORM",             ),
	143:        ("DXGI_FORMAT_ASTC_5X5_UNORM_SRGB",        ),
	145:        ("DXGI_FORMAT_ASTC_6X5_TYPELESS",          ),
	146:        ("DXGI_FORMAT_ASTC_6X5_UNORM",             ),
	147:        ("DXGI_FORMAT_ASTC_6X5_UNORM_SRGB",        ),
	149:        ("DXGI_FORMAT_ASTC_6X6_TYPELESS",          ),
	150:        ("DXGI_FORMAT_ASTC_6X6_UNORM",             ),
	151:        ("DXGI_FORMAT_ASTC_6X6_UNORM_SRGB",        ),
	153:        ("DXGI_FORMAT_ASTC_8X5_TYPELESS",          ),
	154:        ("DXGI_FORMAT_ASTC_8X5_UNORM",             ),
	155:        ("DXGI_FORMAT_ASTC_8X5_UNORM_SRGB",        ),
	157:        ("DXGI_FORMAT_ASTC_8X6_TYPELESS",          ),
	158:        ("DXGI_FORMAT_ASTC_8X6_UNORM",             ),
	159:        ("DXGI_FORMAT_ASTC_8X6_UNORM_SRGB",        ),
	161:        ("DXGI_FORMAT_ASTC_8X8_TYPELESS",          ),
	162:        ("DXGI_FORMAT_ASTC_8X8_UNORM",             ),
	163:        ("DXGI_FORMAT_ASTC_8X8_UNORM_SRGB",        ),
	165:        ("DXGI_FORMAT_ASTC_10X5_TYPELESS",         ),
	166:        ("DXGI_FORMAT_ASTC_10X5_UNORM",            ),
	167:        ("DXGI_FORMAT_ASTC_10X5_UNORM_SRGB",       ),
	169:        ("DXGI_FORMAT_ASTC_10X6_TYPELESS",         ),
	170:        ("DXGI_FORMAT_ASTC_10X6_UNORM",            ),
	171:        ("DXGI_FORMAT_ASTC_10X6_UNORM_SRGB",       ),
	173:        ("DXGI_FORMAT_ASTC_10X8_TYPELESS",         ),
	174:        ("DXGI_FORMAT_ASTC_10X8_UNORM",            ),
	175:        ("DXGI_FORMAT_ASTC_10X8_UNORM_SRGB",       ),
	177:        ("DXGI_FORMAT_ASTC_10X10_TYPELESS",        ),
	178:        ("DXGI_FORMAT_ASTC_10X10_UNORM",           ),
	179:        ("DXGI_FORMAT_ASTC_10X10_UNORM_SRGB",      ),
	181:        ("DXGI_FORMAT_ASTC_12X10_TYPELESS",        ),
	182:        ("DXGI_FORMAT_ASTC_12X10_UNORM",           ),
	183:        ("DXGI_FORMAT_ASTC_12X10_UNORM_SRGB",      ),
	185:        ("DXGI_FORMAT_ASTC_12X12_TYPELESS",        ),
	186:        ("DXGI_FORMAT_ASTC_12X12_UNORM",           ),
	187:        ("DXGI_FORMAT_ASTC_12X12_UNORM_SRGB",      ),
	0xffffffff: ("DXGI_FORMAT_FORCE_UINT",                 ),
}

class UnsupportedFile(Exception): pass

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
		if self.flags & self.Flags.ALPHA:
			raise UnsupportedFile()
		if self.flags & self.Flags.FOURCC:
			self.four_cc = four_cc
			self.format = struct.unpack('<I', self.four_cc)[0]
		if self.flags & self.Flags.RGB: # uncompressed
			self.rgb_bit_count = rgb_bit_count
			self.r_bit_mask = r_bit_mask
			self.g_bit_mask = g_bit_mask
			self.b_bit_mask = b_bit_mask
		if self.flags & self.Flags.YUV:
			raise UnsupportedFile()
		if self.flags & self.Flags.LUMINANCE:
			raise UnsupportedFile()


	def __str__(self):
		ret = []
		ret.append('Pixel Format Flags: 0x%x' % self.flags)
		if self.flags & self.Flags.FOURCC:
			if self.format in d3d9_pixel_formats:
				name = d3d9_pixel_formats[self.format][0]
				ret.append('Format: %s (%i)' % (name, self.format))
			else:
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
		if self.dxgi_format in dxgi_formats:
			name = dxgi_formats[self.dxgi_format][0]
			ret.append('DXGI Format: %s (%i)' % (name, self.dxgi_format))
		else:
			ret.append('DXGI Format: %i' % self.dxgi_format)
		ret.append('Resource Dimension: %s' % self.RESOURCE_DIMENSION[self.dimension])
		ret.append('Array Size: %i' % self.array_size)
		ret.append('Misc Flags 1: 0x%x' % self.misc_flags)
		ret.append('Misc Flags 2: 0x%x' % self.misc_flags2)
		assert(self.dimension == 3) # If this fails I'll need support for Texture1D and/or Texture3D files
		assert(self.array_size == 1) # If this fails I'll need to add a loop to extract resource arrays
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

def _convert(src_filename, pos, header, dest_filename, np_dtype, img_type, converter):
	fp = open(src_filename, 'rb')
	fp.seek(pos)

	buf = np.fromfile(fp, np_dtype, count=header.width * header.height)

	if converter:
		try:
			buf = converter(buf, header)
		except TypeError:
			buf = converter(buf)

	if isinstance(buf, Image.Image):
		image = buf
	elif img_type == 'RGB':
		image = Image.fromstring(img_type, (header.width, header.height), buf.tostring(), 'raw', img_type, 0, 1)
	else:
		image = Image.frombuffer(img_type, (header.width, header.height), buf.data, 'raw', img_type, 0, 1)

	if img_type == 'RGBA' and args.no_alpha:
		image = image.convert('RGB')

	if args.flip:
		image = image.transpose(Image.FLIP_TOP_BOTTOM)

	image.save(dest_filename)

def convert(fp, header, dtype):
	try:
		(fmt_name, np_dtype, img_type, converter) = dtype
	except ValueError:
		print('\nFormat not supported for conversion to PNG')
		return

	filename = '%s.png' % os.path.splitext(fp.name)[0]

	if not args.force:
		if os.path.exists(filename):
			print('\n%s already exists' % filename)
			return
	print('\nConverting to %s...' % filename)
	if pool:
		result = pool.apply_async(_convert, (fp.name, fp.tell(), header, filename, np_dtype, img_type, converter))
		# For debugging:
		# print(result.get())
	else:
		_convert(fp.name, fp.tell(), header, filename, np_dtype, img_type, converter)


def convert_dx10(fp, header):
	if header.dx10_header.dxgi_format not in dxgi_formats:
		return

	# TODO: arrays, etc.

	dtype = dxgi_formats[header.dx10_header.dxgi_format]

	convert(fp, header, dtype)

def convert_fourcc(fp, header):
	# NOTE: Documentation notes that DDS files should not store the format
	# D3DFORMAT / DXGI_FORMAT here as they cannot be distinguished. But
	# it seems they do anyway, so support what we can. Might need to add a
	# flag to choose between the two if this becomes a problem in practice.

	if header.pixel_format.format not in d3d9_pixel_formats:
		return

	dtype = d3d9_pixel_formats[header.pixel_format.format]

	convert(fp, header, dtype)

def convert_pixelformat(fp, header):
	# If these fail I will need a converter:
	assert(header.pixel_format.flags & DDSPixelFormat.Flags.RGB)
	assert(header.pixel_format.flags & DDSPixelFormat.Flags.ALPHAPIXELS)
	assert(header.pixel_format.rgb_bit_count == 32)
	assert(header.pixel_format.r_bit_mask == 0x000000ff)
	assert(header.pixel_format.g_bit_mask == 0x0000ff00)
	assert(header.pixel_format.b_bit_mask == 0x00ff0000)
	assert(header.pixel_format.a_bit_mask == 0xff000000)

	if header.pixel_format.flags & DDSPixelFormat.Flags.ALPHAPIXELS:
		img_type = 'RGBA'
	else:
		img_type = 'RGB'

	np_dtype = {
		8: np.uint8,
		16: np.uint16,
		32: np.uint32,
		64: np.uint64,
	}[header.pixel_format.rgb_bit_count]

	convert(fp, header, (None, np_dtype, img_type, None))

def parse_args():
	import argparse
	global args

	parser = argparse.ArgumentParser(description = 'DDS info & conversion script')
	parser.add_argument('files', nargs='+',
			help='List of DDS files to process')
	parser.add_argument('--no-convert', action='store_true',
			help='Do not convert the image to a PNG, just list info from headers')
	parser.add_argument('--flip', action='store_true',
			help='Flip image upside down')
	parser.add_argument('--gamma', type=float, default=2.2,
			help='Gamma correction to apply')
	parser.add_argument('--hdr', action='store_true',
			help='Scale output to squash high dynamic range')
	parser.add_argument('--auto-scale', action='store_true',
			help='Scale output to maximise range')
	parser.add_argument('--no-alpha', action='store_true',
			help='Drop the alpha channel during conversion')
	parser.add_argument('--force', action='store_true',
			help='Overwrite destination files')
	parser.add_argument('--single-process', '--single-threaded', action='store_true',
			help='Only process one file at a time')
	args = parser.parse_args()

def main():
	global pool

	parse_args()

	if not args.single_process and Image is not None and not args.no_convert:
		pool = multiprocessing.Pool()

	print_line = False
	for file in args.files:
		print_line = print_line and print('\n' + '-'*79 + '\n') or True
		print(file + ':')
		fp = open(file, 'rb')
		try:
			header = DDSHeader(fp)
		except UnsupportedFile as e:
			print('Unsupported file!')
			continue

		print(header)

		if Image is None or args.no_convert: # PIL not installed
			continue

		if header.pixel_format.flags & DDSPixelFormat.Flags.FOURCC:
			if header.dx10_header is not None:
				convert_dx10(fp, header)
			else:
				convert_fourcc(fp, header)
		else:
			convert_pixelformat(fp, header)

	if pool:
		pool.close()
		print('\nWaiting for worker processes to finish...')
		pool.join()

if __name__ == '__main__':
	multiprocessing.freeze_support()
	main()

# vi:noexpandtab:sw=8:ts=8
