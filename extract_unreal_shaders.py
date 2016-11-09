#!/usr/bin/env python3

from extract_unity_shaders import fnv_3Dmigoto_shader
import sys, os, struct, argparse, codecs

verbosity = 0

def pr_debug(*msg, **kwargs):
	if verbosity:
		print(*msg, **kwargs)


class file_parser(object):
	def __init__(self, filename):
		self.f = open(filename, 'rb')
	def u16(self):
		return struct.unpack('<H', self.f.read(2))[0]
	def u32(self):
		return struct.unpack('<I', self.f.read(4))[0]
	def s32(self):
		return struct.unpack('<i', self.f.read(4))[0]
	def read(self, length):
		return self.f.read(length)
	def unknown(self, len, show=True, text='Unknown'):
		if not len:
			return
		start = self.f.tell()
		buf = self.read(len)

		if not verbosity or not show:
			return buf

		width = 16
		pr_debug('%s (%u bytes):' % (text, len), end='')
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
	def find(self, sub, start, end):
		pos = self.f.tell()
		buf = self.f.read(end)
		self.f.seek(pos)
		r = buf.find(sub, start, end)
		if r == -1:
			raise ItemError(r)
		return r

def TArrayU8(f):
	# Engine/Source/Runtime/Core/Public/Containers/Array.h operator<<
	ArrayNum = f.s32()
	return f.read(ArrayNum)

class FString(object):
	def __init__(self, f):
		# Engine/Source/Runtime/Core/Private/Containers/String.cpp operator<<
		SaveNum = f.s32()
		LoadUCS2Char = SaveNum < 0
		SaveNum = abs(SaveNum)
		# pr_debug('SaveNum: %i' % SaveNum)
		if LoadUCS2Char:
			self.raw = f.read(SaveNum * 2)
			self.encoding = 'utf16'
		else:
			self.raw = f.read(SaveNum)
			self.encoding = 'ascii'
		self.string = self.raw.decode(self.encoding).rstrip('\0')

	def __str__(self):
		return self.string

	def __bytes__(self):
		return self.raw

def FHash(f):
	return codecs.encode(f.read(20), 'hex').decode('ascii')

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
		print('Type:', Type)
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

		# XXX: Could potentially work backwards from below to find the
		# preceeding fields we skipped over. It is worth noting that OutputHash
		# in this section is repeated after the code if the shader is inlined.

		off = f.find(bytes(Type), 0, EndOffset - f.tell())
		f.unknown(off, text='Skipping due to fields with shader specific length')
		# Ar << Type;
		f.seek(f.tell() + len(bytes(Type)))

		SourceHash = FHash(f)
		pr_debug('SourceHash:', SourceHash)

		# Engine/Source/Runtime/ShaderCore/Public/ShaderCore.h
		#   friend FArchive& operator<<(FArchive& Ar,FShaderTarget& Target)
		TargetFrequency = f.u32()
		TargetPlatform = f.u32()
		pr_debug('TargetFrequency: %u, TargetPlatform: %u' % (TargetFrequency, TargetPlatform))

		NumUniformParameters = f.s32()
		print('NumUniformParameters: %i' % NumUniformParameters)
		for ParameterIndex in range(NumUniformParameters):
			StructName = FString(f)
			print('  StructName: %s' % StructName)
			# Grrr! The fields here can be parameter type specific:
			#   FUniformBufferStruct* Struct = FindUniformBufferStructByName(*StructName);
			#   FShaderUniformBufferParameter* Parameter = Struct ? Struct->ConstructTypedParameter() : new FShaderUniformBufferParameter();
			# With any luck they are all generic, but if not this could be a
			# deal breaker. If they are generic this should work:
			#   UnrealEngine/Engine/Source/Runtime/ShaderCore/Public/ShaderParameters.h
			#   FShaderUniformBufferParameter::Serialize()
			BaseIndex = f.u16() # NOTE: There is an accessor method that casts this to 32bit
			bIsBound = f.u32() # A bool... God damnit, read a book on defining file formats
			print('   BaseIndex: %u, bIsBound: %u' % (BaseIndex, bIsBound))

		# And again - way to have a flag embedded in the file to indicate that
		# this section is present @Epic Fail...
		bShadersInline = True
		if bShadersInline:
			# Engine/Source/Runtime/ShaderCore/Private/Shader.cpp
			#   FShaderResource::Serialize
			#     FArchive& operator<<(FArchive& Ar,FShaderType*& Ref)
			ShaderTypeName = FString(f)
			pr_debug('ShaderTypeName:', ShaderTypeName)
			TargetFrequency1 = f.u32()
			TargetPlatform1 = f.u32()
			assert(TargetFrequency == TargetFrequency1)
			assert(TargetPlatform == TargetPlatform1)
			#     Ar << Code;
			Code = TArrayU8(f)
			OutputHash = FHash(f)
			pr_debug('OutputHash:', OutputHash) # Repeated from above in the section we skipped over
			NumInstructions = f.u32()
			pr_debug('NumInstructions:', NumInstructions)
			NumTextureSamplers = f.u32()
			pr_debug('NumTextureSamplers:', NumTextureSamplers)
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
