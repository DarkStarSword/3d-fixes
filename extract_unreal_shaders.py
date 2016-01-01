#!/usr/bin/env python3

from extract_unity_shaders import fnv_3Dmigoto_shader
import sys, os, struct

enable_debug = False

def pr_debug(*msg, **kwargs):
	if enable_debug:
		print(*msg, file=sys.stderr, **kwargs)


class file_parser(object):
	def __init__(self, filename):
		self.f = open(filename, 'rb')
	def u32(self):
		return struct.unpack('<I', self.f.read(4))[0]
	def s32(self):
		return struct.unpack('<i', self.f.read(4))[0]
	def read(self, length):
		return self.f.read(length)
	def unknown(self, len, show=True):
		buf = self.read(len)

		if not enable_debug or not show:
			return buf

		width = 16
		pr_debug('Unknown: ', end='')
		a = ''
		for i, b in enumerate(buf):
			if i % width == 0:
				if i:
					pr_debug(' | %s |' % a)
				else:
					pr_debug()
				pr_debug('  %08x: ' % self.f.tell(), end='')
				a = ''
			elif i and i % 4 == 0:
				pr_debug(' ', end='')
			if b >= ord(' ') and b <= ord('~'):
				a += chr(b)
			else:
				a += '.'
			pr_debug('%02X' % b, end='')
		if a:
			rem = width - (i % width) - 1
			pr_debug(' ' * (rem*2), end='')
			pr_debug(' ' * (rem//4 + 1), end='')
			pr_debug('| %s%s |' % (a, ' ' * rem))
		return buf
	def tell(self):
		return self.f.tell()
	def seek(self, *a, **kw):
		return self.f.seek(*a, **kw)
	def fileno(self):
		return self.f.fileno()


def FString(f):
	# Engine/Source/Runtime/Core/Private/Containers/String.cpp operator<<
	SaveNum = f.s32()
	LoadUCS2Char = SaveNum < 0
	SaveNum = abs(SaveNum)
	# pr_debug('SaveNum: %i' % SaveNum)
	if LoadUCS2Char:
		string = f.read(SaveNum * 2).decode('utf16')
	else:
		string = f.read(SaveNum).decode('ascii')
	return string.rstrip('\0')

def parse_cooked_shader_cache(f):
	'''
	Parses a cooked shader cache from UE4, e.g.
	*/CookedPCConsole/GlobalShaderCache-PC-D3D-SM5.bin

	Material shaders and uncooked shaders are elsewhere and not parsed yet

	This might be specific to Arkham Knight for now
	'''
	# Engine/Source/Runtime/Engine/Private/GlobalShader.cpp SerializeGlobalShaders
	assert(f.u32() == 0x47534D42) # Endian swapped "GSMB"

	ret = {}

	# NFI - can't see this in the source code anywhere:
	f.unknown(17)

	# Engine/Source/Runtime/ShaderCore/Public/Shader.h TShaderMap::SerializeInline
	NumShaders = f.u32()
	print('NumShaders: %i' % NumShaders)

	for i in range(NumShaders):
		print()

		# # Engine/Source/Runtime/ShaderCore/Private/Shader.cpp FArchive operator<<
		# Type = FString(f)
		# pr_debug('Type:', Type)
		# EndOffset = f.u32()
		# pr_debug('EndOffset: 0x%x' % EndOffset)
		# # if True: # bHandleShaderKeyChanges
		# # 	# FSHAHash MaterialShaderMapHash 
		# # 	# FString VertexFactoryTypeName
		# # 	# FSHAHash VFSourceHash
		# # 	# FSerializationHistory VFSerializationHistory
		# # 	# FString ShaderTypeName
		# # 	# FSHAHash SourceHash
		# # 	# FSerializationHistory SerializationHistory
		# # 	# FShaderTarget Target;

		# Format used in Batman does not seem to match UE4 source code?
		# Either that or I'm lost in a maze of object inheritance, all
		# alike. Screw the source code, it doesn't match Batman and
		# it's taking longer than my usual reverse engineering approach

		Name = FString(f)
		print('Name:', Name)

		u1 = f.unknown(8)
		u2 = f.unknown(20)

		EndOffset = f.u32()
		pr_debug('EndOffset: 0x%x' % EndOffset)

		# Possibly an index of resources?
		table_len = f.u32()
		pr_debug('Unknown Table Length: %i\n ' % table_len, end='')
		for j in range(table_len):
			u = f.u32()
			pr_debug("%i, " % u, end='')
		pr_debug()

		f.unknown(2)

		bytecode_len = f.u32()
		pr_debug('Bytecode Len:', bytecode_len)

		bytecode = f.read(bytecode_len)
		# pr_debug('Bytecode:', bytecode)
		assert(bytecode[0:4] == b'DXBC')

		fnv = fnv_3Dmigoto_shader(bytecode)
		print('3DMigoto hash: %016x' % fnv)

		u1a = f.unknown(8, show=False)
		assert(u1 == u1a)

		Name1 = FString(f)
		# pr_debug('Name1:', Name)
		if Name != Name1:
			print('Names differ!')

		u2a = f.unknown(20, show=False)
		assert(u2 == u2a)

		tail = EndOffset - f.tell()
		f.unknown(tail)

		ret[fnv] = Name

	print()

	cur = f.tell()
	end = os.fstat(f.fileno()).st_size
	pr_debug('Current position: 0x%x / 0x%x' % (cur, end))
	f.unknown(end - cur)

	return ret

def main():
	f = file_parser(sys.argv[1])
	shader_names = parse_cooked_shader_cache(f)

	for shader in sys.argv[2:]:
		fnv = int(os.path.basename(shader)[0:16], 16)
		if fnv in shader_names:
			print('%s: %s' % (shader, shader_names[fnv]))


if __name__ == '__main__':
	main()
