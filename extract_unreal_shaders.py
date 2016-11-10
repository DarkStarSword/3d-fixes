#!/usr/bin/env python3

from extract_unity_shaders import fnv_3Dmigoto_shader
from extract_unity_shaders import export_dx11_shader
from extract_unity_shaders import add_vanity_tag
from extract_unity_shaders import commentify
import sys, os, struct, argparse, codecs, hashlib, io

verbosity = 0

def pr_debug(*msg, **kwargs):
	if verbosity:
		print(*msg, **kwargs)

headers = None

def start_headers():
	global headers
	headers = io.StringIO()

def end_headers():
	global headers
	ret = headers.getvalue().splitlines(True)
	add_vanity_tag(ret)
	headers = None
	return commentify(ret)

def pr_headers(*msg, **kwargs):
	global headers
	if headers is not None:
		print(*msg, file=headers, **kwargs)
	pr_debug(*msg, **kwargs)

def hexdump(buf, text, start=0, width=16):
	a = ''
	pr_headers(text, end=':')
	for i, b in enumerate(buf):
		if i % width == 0:
			if i:
				pr_headers(' | %s |' % a)
			else:
				pr_headers()
			pr_headers('  %08x: ' % (start + i), end='')
			a = ''
		elif i and i % 4 == 0:
			pr_headers(' ', end='')
		if b >= ord(' ') and b <= ord('~'):
			a += chr(b)
		else:
			a += '.'
		pr_headers('%02X' % b, end='')
	if a:
		rem = width - (i % width) - 1
		pr_headers(' ' * (rem*2), end='')
		pr_headers(' ' * (rem//4 + 1), end='')
		pr_headers('| %s%s |' % (a, ' ' * rem))

class parser(object):
	def u16(self):
		return struct.unpack('<H', self.f.read(2))[0]
	def s16(self):
		return struct.unpack('<h', self.f.read(2))[0]
	def u32(self):
		return struct.unpack('<I', self.f.read(4))[0]
	def s32(self):
		return struct.unpack('<i', self.f.read(4))[0]
	def u64(self):
		return struct.unpack('<Q', self.f.read(8))[0]
	def s64(self):
		return struct.unpack('<q', self.f.read(8))[0]
	def bool(self):
		b, = struct.unpack('<I', self.f.read(4))
		assert (b == 0 or b == 1)
		return not not b
	def read(self, length=None):
		return self.f.read(length)
	def unknown(self, len, show=True, text='Unknown'):
		if not len:
			return
		start = self.f.tell()
		buf = self.read(len)

		if not show:
			return buf

		hexdump(buf, '%s (%u bytes)' % (text, len), start=start)
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

class file_parser(parser):
	def __init__(self, filename):
		self.f = open(filename, 'rb')

class buf_parser(parser):
	def __init__(self, buf):
		self.f = io.BytesIO(buf)

def TArrayU8(f):
	# Engine/Source/Runtime/Core/Public/Containers/Array.h operator<<
	ArrayNum = f.s32()
	return f.read(ArrayNum)

def TArrayU32(f):
	# Engine/Source/Runtime/Core/Public/Containers/Array.h operator<<
	ArrayNum = f.s32()
	return struct.unpack('%iI' % ArrayNum, f.read(ArrayNum * 4))

def TArrayS32(f):
	ArrayNum = f.s32()
	return struct.unpack('%ii' % ArrayNum, f.read(ArrayNum * 4))

def TArrayObject(f, constructor, *args, **kwargs):
	ArrayNum = f.s32()
	ret = []
	for i in range(ArrayNum):
		ret.append(constructor(f, *args, **kwargs))
	return ret

def FGuid(f):
	return('%08x-%08x-%08x-%08x' % struct.unpack('4I', f.read(16)))

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

	def __eq__(self, other):
		return self.raw == other.raw

def FHash(f):
	return codecs.encode(f.read(20), 'hex').decode('ascii')

def shader_hash(bytecode):
	if args.hash == 'embedded':
		# The embedded hash is a 16 byte hash, but we only use 8:
		return int(codecs.encode(bytecode[4:12], 'hex'), 16)
	if args.hash == '3dmigoto':
		return fnv_3Dmigoto_shader(bytecode)
	raise NotImplemented()

def export_shader(bytecode):
	assert(bytecode[0:4] == b'DXBC')
	# TODO: Support other 3DMigoto hash types

	headers = end_headers()

	hash = shader_hash(bytecode)
	# FIXME: Determine shader type somehow
	base_filename = 'extracted/%016x-XX' % hash
	try:
		os.mkdir('extracted')
	except FileExistsError:
		pass

	export_dx11_shader(base_filename, bytecode, headers)

def parse_ue4_shader_code(Code):
	f = buf_parser(Code)

	# Engine/Source/Runtime/ShaderCore/Public/ShaderCore.h
	#   inline FArchive& operator<<(FArchive& Ar, FBaseShaderResourceTable& SRT)
	ResourceTableBits = f.u32()
	ShaderResourceViewMap = TArrayU32(f)
	SamplerMap = TArrayU32(f)
	UnorderedAccessViewMap = TArrayU32(f)
	ResourceTableLayoutHashes = TArrayU32(f)
	pr_headers('ResourceTableBits:', '%08x' % ResourceTableBits)
	pr_headers('ShaderResourceViewMap:',     ' '.join(map(lambda x: '%08x' % x, ShaderResourceViewMap)))
	pr_headers('SamplerMap:',                ' '.join(map(lambda x: '%08x' % x, SamplerMap)))
	pr_headers('UnorderedAccessViewMap:',    ' '.join(map(lambda x: '%08x' % x, UnorderedAccessViewMap)))
	pr_headers('ResourceTableLayoutHashes:', ' '.join(map(lambda x: '%08x' % x, ResourceTableLayoutHashes)))

	# This is in the UE4 source, but doesn't seem to be in the file?
	# Different engine versions perhaps? The tail in ABZU is different.
	# Engine/Source/Developer/Windows/ShaderFormatD3D/Private/D3D11ShaderCompiler.cpp
	# CompileD3D11Shader() - search for Output.Code
	#   Output.Code.Add(bGlobalUniformBufferUsed);
	#   Output.Code.Add(NumSamplers);
	#   Output.Code.Add(NumSRVs);
	#   Output.Code.Add(NumCBs);
	#   Output.Code.Add(NumUAVs);
	#  Note - if these are present, they should be *one byte* each

	# I'm not sure where the source is corresponding to this tail - I might
	# need to see what has changed since the last time I pulled the UE4 source
	# Looks like it contains the .usf filename and some other useful info...
	tail_len = Code[-1]
	hexdump(Code[-tail_len:-1], 'Unknown Tail (%u bytes)' % (tail_len - 1))

	return Code[f.tell() : -tail_len]

def parse_ue4_shader(f):
	start_headers()
	Type = FString(f)
	pr_headers('Type:', Type)
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
	f.unknown(off, text='Skipping over variable length shader specific section')
	# Ar << Type;
	f.seek(f.tell() + len(bytes(Type)))

	SourceHash = FHash(f)
	pr_headers('SourceHash:', SourceHash)

	# Engine/Source/Runtime/ShaderCore/Public/ShaderCore.h
	#   friend FArchive& operator<<(FArchive& Ar,FShaderTarget& Target)
	TargetFrequency = f.u32()
	TargetPlatform = f.u32()
	pr_headers('TargetFrequency: %u, TargetPlatform: %u' % (TargetFrequency, TargetPlatform))

	NumUniformParameters = f.s32()
	pr_headers('NumUniformParameters: %i' % NumUniformParameters)
	for ParameterIndex in range(NumUniformParameters):
		StructName = FString(f)
		pr_headers('  StructName: %s' % StructName)
		# Grrr! The fields here can be parameter type specific:
		#   FUniformBufferStruct* Struct = FindUniformBufferStructByName(*StructName);
		#   FShaderUniformBufferParameter* Parameter = Struct ? Struct->ConstructTypedParameter() : new FShaderUniformBufferParameter();
		# With any luck they are all generic, but if not this could be a
		# deal breaker. If they are generic this should work:
		#   UnrealEngine/Engine/Source/Runtime/ShaderCore/Public/ShaderParameters.h
		#   FShaderUniformBufferParameter::Serialize()
		BaseIndex = f.u16() # NOTE: There is an accessor method that casts this to 32bit
		bIsBound = f.u32() # A bool... God damnit, read a book on defining file formats
		pr_headers('   BaseIndex: %u, bIsBound: %u' % (BaseIndex, bIsBound))

	# And again - way to have a flag embedded in the file to indicate that
	# this section is present @Epic Fail...
	bShadersInline = True
	if bShadersInline:
		# Engine/Source/Runtime/ShaderCore/Private/Shader.cpp
		#   FShaderResource::Serialize
		#     FArchive& operator<<(FArchive& Ar,FShaderType*& Ref)
		ShaderTypeName = FString(f)
		pr_headers('ShaderTypeName:', ShaderTypeName)
		TargetFrequency1 = f.u32()
		TargetPlatform1 = f.u32()
		assert(TargetFrequency == TargetFrequency1)
		assert(TargetPlatform == TargetPlatform1)
		#     Ar << Code;
		Code = TArrayU8(f)
		dxbc = parse_ue4_shader_code(Code)
		OutputHash = FHash(f)
		pr_headers('OutputHash:', OutputHash) # Repeated from above in the section we skipped over
		NumInstructions = f.u32()
		pr_headers('NumInstructions:', NumInstructions)
		NumTextureSamplers = f.u32()
		pr_headers('NumTextureSamplers:', NumTextureSamplers)

	f.unknown(EndOffset - f.tell())

	export_shader(dxbc)

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
		pr_debug()
		parse_ue4_shader(f)

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

		hash = shader_hash(bytecode)
		print('%s hash: %016x' % (args.hash, hash))

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

		ret[hash] = Name

	print()

	cur = f.tell()
	end = os.fstat(f.fileno()).st_size
	pr_debug('Current position: 0x%x / 0x%x' % (cur, end))
	f.unknown(end - cur)

	return ret

def parse_shader_cache(f):
	if args.batman:
		shader_names = parse_batman_cooked_shader_cache(f)
		for shader in args.files[1:]:
			fnv = int(os.path.basename(shader)[0:16], 16)
			if fnv in shader_names:
				print('%s: %s' % (shader, shader_names[fnv]))
	else:
		parse_ue4_global_shader_cache(f)

def parse_custom_version_section(f, LegacyFileVersion):
	# static ECustomVersionSerializationFormat::Type GetCustomVersionFormatForArchive(int32 LegacyFileVersion)
	# Engine/Source/Runtime/Core/Private/Serialization/CustomVersion.cpp
	if LegacyFileVersion < -5: # Optimized
		# TSet, which contains a TSparseArray, which stores number of elements
		# followed by a list, the serizlisation of each should be in
		# Engine/Source/Runtime/Core/Private/Serialization/CustomVersion.cpp:
		NewNumElements = f.s32()
		# In ABZU this is 0, assert that for now and deal with it later:
		assert(NewNumElements == 0)
	elif LegacyFileVersion < -2: # Guids
		raise NotImplemented()
	elif LegacyFileVersion == -2: # Enums
		raise NotImplemented()

class Parser(object):
	def __init__(self, indent=0):
		self.indent = indent

	def parse(self, name, val, fmt='{}'):
		pr_debug(('{}{}: %s' % fmt).format(' ' * self.indent, name, val))
		setattr(self, name, val)

class Generation(Parser):
	def __init__(self, f, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		p('ExportCount', f.s32())
		p('NameCount', f.s32())

class FEngineVersion(Parser):
	def __init__(self, f, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		p('Major', f.s16())
		p('Minor', f.s16())
		p('Patch', f.s16())
		p('Changelists', f.u32())
		p('Branch', FString(f))

class FCompressedChunk(Parser):
	def __init__(self, f, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		p('UncompressedOffset', f.s32())
		p('UncompressedSize', f.s32())
		p('CompressedOffset', f.s32())
		p('CompressedSize', f.s32())

class PackageFileSummary(Parser):
	# Engine/Source/Runtime/CoreUObject/Private/UObject/PackageFileSummary.cpp
	def __init__(self, f, indent=0):
		# FArchive& operator<<( FArchive& Ar, FPackageFileSummary& Sum )
		Parser.__init__(self, indent)
		p = self.parse
		assert(f.u32() == 0x9E2A83C1) # PACKAGE_FILE_TAG / PACKAGE_FILE_TAG_SWAPPED

		# See comment in the source about what this signifies:
		p('LegacyFileVersion', f.s32())
		assert(self.LegacyFileVersion == -6) # ABZU, only one tested
		if self.LegacyFileVersion != -4:
			p('LegacyUE3Version', f.s32())

		p('FileVersionUE4', f.s32())
		p('FileVersionLicenseeUE4', f.s32())

		parse_custom_version_section(f, self.LegacyFileVersion)

		p('TotalHeaderSize', f.s32())
		p('FolderName', FString(f))
		p('PackageFlags', f.u32(), '{:08x}')
		p('NameCount', f.s32())
		p('NameOffset', f.s32(), '0x{:x}')

		if self.FileVersionUE4 >= 459: # VER_UE4_SERIALIZE_TEXT_IN_PACKAGES
			p('GatherableTextDataCount', f.s32())
			p('GatherableTextDataOffset', f.s32(), '0x{:x}')

		p('ExportCount', f.s32())
		p('ExportOffset', f.s32(), '0x{:x}')
		p('ImportCount', f.s32())
		p('ImportOffset', f.s32(), '0x{:x}')
		p('DependsOffset', f.s32(), '0x{:x}')

		assert(self.FileVersionUE4 >= 214) # VER_UE4_OLDEST_LOADABLE_PACKAGE
		assert(self.FileVersionUE4 <= 510) # VER_UE4_AUTOMATIC_VERSION XXX incremented as the format changes

		if self.FileVersionUE4 >= 384: # VER_UE4_ADD_STRING_ASSET_REFERENCES_MAP
			p('StringAssetReferencesCount', f.s32())
			p('StringAssetReferencesOffset', f.s32(), '0x{:x}')

		if self.FileVersionUE4 >= 510: # VER_UE4_ADDED_SEARCHABLE_NAMES
			p('SearchableNamesOffset', f.s32(), '0x{:x}')

		p('ThumbnailTableOffset', f.s32(), '0x{:x}')
		p('Guid', FGuid(f))

		p('GenerationCount', f.s32())
		self.generations = []
		for i in range(self.GenerationCount):
			self.generations.append(Generation(f, indent=2))

		if self.FileVersionUE4 >= 336: # VER_UE4_ENGINE_VERSION_OBJECT
			pr_debug('SavedByEngineVersion:')
			self.SavedByEngineVersion = FEngineVersion(f, indent=2)
		else:
			p('EngineChangelist', f.s32())

		if self.FileVersionUE4 >= 444: # VER_UE4_PACKAGE_SUMMARY_HAS_COMPATIBLE_ENGINE_VERSION
			pr_debug('CompatibleWithEngineVersion:')
			self.CompatibleWithEngineVersion = FEngineVersion(f, indent=2)

		p('CompressionFlags', f.u32(), '{:08x}')
		pr_debug('CompressedChunks:')
		self.CompressedChunks = TArrayObject(f, FCompressedChunk, indent=2)
		p('PackageSource', f.u32(), '{:08x}')
		pr_debug('AdditionalPackagesToCook:')
		self.AdditionalPackagesToCook = TArrayObject(f, FString, indent=2)

		if self.LegacyFileVersion > -7:
			p('NumTextureAllocations', f.s32())

		p('AssetRegistryDataOffset', f.s32(), '0x{:08x}')
		p('BulkDataStartOffset', f.s64(), '0x{:016x}')

		if self.FileVersionUE4 >= 224: # VER_UE4_WORLD_LEVEL_INFO
			p('WorldTileInfoDataOffset', f.s32(), '0x{:08x}')

		if self.FileVersionUE4 >= 326: # VER_UE4_CHANGED_CHUNKID_TO_BE_AN_ARRAY_OF_CHUNKIDS
			p('ChunkIDs', TArrayS32(f))
		elif self.FileVersionUE4 >= 278: # VER_UE4_ADDED_CHUNKID_TO_ASSETDATA_AND_UPACKAGE
			raise NotImplemented()

		if self.FileVersionUE4 >= 507: # VER_UE4_PRELOAD_DEPENDENCIES_IN_COOKED_EXPORTS
			p('PreloadDependencyCount', f.s32())
			p('PreloadDependencyOffset', f.s32(), '0x{:x}')

class FObjectExport(Parser):
	# Engine/Source/Runtime/CoreUObject/Private/UObject/ObjectResource.cpp
	def __init__(self, f, s, FName, indent=0):
		# FArchive& operator<<( FArchive& Ar, FObjectExport& E )
		Parser.__init__(self, indent)
		p = self.parse
		p('ClassIndex', f.s32())
		p('SuperIndex', f.s32())
		if s.FileVersionUE4 >= 508: # VER_UE4_TemplateIndex_IN_COOKED_EXPORTS
			p('TemplateIndex', f.s32())
		p('OuterIndex', f.s32())
		p('ObjectName', FName(f))
		p('ObjectFlags', f.u32(), '{:08x}')
		p('SerialSize', f.s32())
		p('SerialOffset', f.u32(), '0x{:x}')
		p('bForcedExport', f.bool())
		p('bNotForClient', f.bool())
		p('bNotForServer', f.bool())
		p('PackageGuid', FGuid(f))
		p('PackageFlags', f.u32(), '{:08x}')
		if s.FileVersionUE4 >= 365: # VER_UE4_LOAD_FOR_EDITOR_GAME
			p('bNotForEditorGame', f.bool())
		if s.FileVersionUE4 >= 485: # VER_UE4_COOKED_ASSETS_IN_EDITOR_SUPPORT
			p('bIsAsset', f.bool())
		if s.FileVersionUE4 >= 507: # VER_UE4_PRELOAD_DEPENDENCIES_IN_COOKED_EXPORTS
			p('FirstExportDependency', f.s32())
			p('SerializationBeforeSerializationDependencies', f.s32())
			p('CreateBeforeSerializationDependencies', f.s32())
			p('SerializationBeforeCreateDependencies', f.s32())
			p('CreateBeforeCreateDependencies', f.s32())

class FObjectImport(Parser):
	# Engine/Source/Runtime/CoreUObject/Private/UObject/ObjectResource.cpp
	def __init__(self, f, s, FName, indent=0):
		# FArchive& operator<<( FArchive& Ar, FObjectExport& E )
		Parser.__init__(self, indent)
		p = self.parse
		p('ClassPackage', FName(f))
		p('ClassName', FName(f))
		p('OuterIndex', f.s32())
		p('ObjectName', FName(f))

def parse_name_map(f, s):
	# Engine/Source/Runtime/AssetRegistry/Private/PackageReader.cpp
	# FPackageReader::SerializeNameMap()
	f.seek(s.NameOffset)
	names = []
	for i in range(s.NameCount):
		name = FString(f) # Actually an FNameEntrySerialized
		pr_debug('  Name[%i]: %s' % (i, name))
		names.append(name)

	def FNamePackageReader(f, names):
		# There seem to be several implementations of FName, this one is from
		# Engine/Source/Runtime/AssetRegistry/Private/PackageReader.cpp
		NameIndex = f.u32()
		Number = f.u32()
		return '%s[%i]' % (names[NameIndex], Number)

	return lambda f: FNamePackageReader(f, names)

def parse_imports(f, s, FName):
	# Engine/Source/Runtime/AssetRegistry/Private/PackageReader.cpp
	# FPackageReader::SerializeImportMap()
	f.seek(s.ImportOffset)
	imports = []
	for i in range(s.ImportCount):
		pr_debug('Import %i:' % i)
		imports.append(FObjectImport(f, s, FName, indent=2))
	return imports

def parse_exports(f, s, FName):
	# Engine/Source/Runtime/AssetRegistry/Private/PackageReader.cpp
	# FPackageReader::SerializeExportMap()
	f.seek(s.ExportOffset)
	exports = []
	for i in range(s.ExportCount):
		pr_debug('Export %i:' % i)
		exports.append(FObjectExport(f, s, FName, indent=2))

		offset = f.tell()
		f.seek(exports[-1].SerialOffset)
		f.unknown(exports[-1].SerialSize)
		f.seek(offset)
	return exports

def parse_uasset(f):
	# ? Engine/Source/Runtime/AssetRegistry/Private/PackageReader.cpp
	# ? Engine/Source/Runtime/Core/Private/Serialization/Archive.cpp
	# ? Engine/Source/Runtime/CoreUObject/Private/UObject/SavePackage.cpp

	summary = PackageFileSummary(f)
	assert(not (summary.PackageFlags & 0x02000000)) # PKG_StoreCompressed
	FName = parse_name_map(f, summary)
	imports = parse_imports(f, summary, FName)
	exports = parse_exports(f, summary, FName)

def parse_args():
	global verbosity, args

	parser = argparse.ArgumentParser()
	parser.add_argument('files', nargs='+')
	parser.add_argument('--verbose', '-v', action='count', default=0)
	parser.add_argument('--batman', action='store_true')
	parser.add_argument('--hash', choices=['embedded', '3dmigoto'], required=True) # TODO: bytecode
	args = parser.parse_args()

	verbosity = args.verbose

def main():
	parse_args()

	for filename in args.files:
		f = file_parser(filename)
		ext = os.path.splitext(filename)[1].lower()
		if ext == '.bin':
			parse_shader_cache(f)
		elif ext == '.uasset':
			parse_uasset(f)
		else:
			raise Exception('Unsupported file: %s' % filename)



if __name__ == '__main__':
	main()

# vi:noet:ts=4:sw=4
