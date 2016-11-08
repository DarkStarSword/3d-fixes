#!/usr/bin/env python3

from extract_unity_shaders import fnv_3Dmigoto_shader
import sys, os, struct, argparse

verbosity = 0

def pr_debug(*msg, **kwargs):
	if verbosity:
		print(*msg, **kwargs)


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
		start = self.f.tell()
		buf = self.read(len)

		if not verbosity or not show:
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
				pr_debug('  %08x: ' % (start + i), end='')
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

def parse_ue4_global_shader_cache(f):
	'''
	e.g. Engine/GlobalShaderCache-PCD3D_SM5.bin
	'''
	# Engine/Source/Runtime/Engine/Private/GlobalShader.cpp SerializeGlobalShaders
	assert(f.u32() == 0x47534D42) # Endian swapped "GSMB"

	# Engine/Source/Runtime/ShaderCore/Public/Shader.h TShaderMap::SerializeInline
	NumShaders = f.u32()
	print('NumShaders: %i' % NumShaders)

	for i in range(NumShaders):
		print()

		Type = FString(f)
		pr_debug('Type:', Type)
		EndOffset = f.u32()
		pr_debug('EndOffset: 0x%x' % EndOffset)

		# Way to have a flag embedded >in the file< indicating if this section
		# is present or not @Epic... Fail...
		bHandleShaderKeyChanges = False
		if bHandleShaderKeyChanges:
			# Engine/Source/Runtime/ShaderCore/Private/Shader.cpp
			#   FArchive& operator<<(FArchive& Ar,class FSelfContainedShaderId& Ref)
			#
			# Engine/Source/Runtime/Core/Public/Misc/SecureHash.h
			#   FSHAHash MaterialShaderMapHash - 16 bytes
			# FString VertexFactoryTypeName
			# FSHAHash VFSourceHash
			# FSerializationHistory VFSerializationHistory
			# FString ShaderTypeName
			# FSHAHash SourceHash
			# FSerializationHistory SerializationHistory
			# FShaderTarget Target;
			assert(False)

		# XXX: This file format is NOT WELL DEFINED and that is an EPIC FAIL!
		# The fields in this section may be SHADER SPECIFIC & GAME SPECIFIC!
		# There is no field that indicates the length of this section, so we
		# cannot reliably skip over it to get to the generic info we are after.
		# We take advantage of the fact that the shader type string is repeated
		# in the generic info after this section (which itself shows how poorly
		# designed the format is, but whatever - at least it is something we
		# can use. @Epic, if you fix that, please add a length field so we can
		# skip over the shader type specifc fields that we don't care about).
		# Look for any class that is derived from FShader (or other children
		# like FGlobalShader, etc) that has a ::Serialize() method. e.g.
		# Engine/Source/Runtime/Renderer/Private/ShaderBaseClasses.cpp
		# Engine/Source/Runtime/SlateRHIRenderer/Private/SlateMaterialShader.cpp
		# Engine/Source/Runtime/SlateRHIRenderer/Private/SlateShaders.cpp
		# And of course... these can be defined/overridden on a per game basis,
		# so the source code to the engine only helps us in some cases :(

		# Engine/Source/Runtime/ShaderCore/Private/Shader.cpp
		#   bool FShader::SerializeBase(FArchive& Ar, bool bShadersInline)

		# Ar << OutputHash;
		# Ar << MaterialShaderMapHash;
		# Ar << VFType;
		# Ar << VFSourceHash;
		# Ar << Type;
		# Ar << SourceHash;
		# Ar << Target;
		# NumUniformParameters = f.s32()
		# print('NumUniformParameters: %i' % NumUniformParameters)
		# for ParameterIndex in range(NumUniformParameters):
		# 	StructName = FString(f)
		# 	print('StructName: %s' % StructName)
		# 	# FShaderUniformBufferParameter* Parameter = Struct ? Struct->ConstructTypedParameter() : new FShaderUniformBufferParameter();
		# 	# Ar << *Parameter;

		# And again - way to have a flag embedded in the file to indicate that
		# this section is present @Epic Fail...
		bShadersInline = True
		if bShadersInline:
			# Resource->Serialize(Ar)
			#   Ar << SpecificType;
			#   Ar << Target;
			#    Ar << TargetFrequency << TargetPlatform;
			#   Ar << Code;
			#   Ar << OutputHash;
			#   Ar << NumInstructions;
			#   Ar << NumTextureSamplers;
			pass

		tail = EndOffset - f.tell()
		f.unknown(tail)

	print()

	cur = f.tell()
	end = os.fstat(f.fileno()).st_size
	pr_debug('Current position: 0x%x / 0x%x' % (cur, end))
	f.unknown(end - cur)

def parse_batman_cooked_shader_cache(f):
	'''
	Parses a cooked shader cache from UE3.5, e.g.
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

		# Format used in Batman does not seem to match UE4 source code?
		# Update: Batman is a heavily modified version of UE3.5, not UE4

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

def parse_args():
	global verbosity

	parser = argparse.ArgumentParser()
	parser.add_argument('files', nargs='+')
	parser.add_argument('--verbose', '-v', action='count', default=0)
	parser.add_argument('--batman', action='store_true')
	args = parser.parse_args()

	verbosity = args.verbose

	return args

def main():
	args = parse_args()

	f = file_parser(args.files[0])
	if args.batman:
		shader_names = parse_batman_cooked_shader_cache(f)
		for shader in args.files[1:]:
			fnv = int(os.path.basename(shader)[0:16], 16)
			if fnv in shader_names:
				print('%s: %s' % (shader, shader_names[fnv]))
	else:
		parse_ue4_global_shader_cache(f)



if __name__ == '__main__':
	main()

# vi:noet:ts=4:sw=4
