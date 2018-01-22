#!/usr/bin/env python3

import sys, os, struct, itertools, codecs, io, argparse

def read_cstring(file):
    s = b''
    while True:
        c = file.read(1)
        if c == '' or c == b'\0':
            return s
        s += c

def hexdump(buf, start=0, width=16, indent=0):
	a = ''
	for i, b in enumerate(buf):
		if i % width == 0:
			if i:
				print(' | %s |' % a)
			print('%s  %08x: ' % (' ' * indent, start + i), end='')
			a = ''
		elif i and i % 4 == 0:
			print(' ', end='')
		if b >= ord(' ') and b <= ord('~'):
			a += chr(b)
		else:
			a += '.'
		print('%02X' % b, end='')
	if a:
		rem = width - (i % width) - 1
		print(' ' * (rem*2), end='')
		print(' ' * (rem//4 + 1), end='')
		print('| %s%s |' % (a, ' ' * rem))

type_map = {
        0x80000031: 'array',
        0x8000004c: 'bool',
        0x80000051: 'char',
        0x800000a1: 'float',
        0x800000de: 'int',
        0x800000f1: 'string_map',
        0x8000021f: 'string_map_entry',
        0x8000032e: 'u64',
        0x80000335: 'byte',
        0x80000348: 'string',
        0x8000038b: 'half',
        0x800003a0: 'blob', # Same as byte?
        0x800003a6: 'unsigned',
        0x800003d5: 'struct', # ? flags & 0x8000
}

name_map = {
        0x8000031b: 'length',
}

def decode_embedded_type_info(file):
    # TODO: Actually might want to parse this, as it describes the
    # data structure hardcoded in extract_unity55_shaders, which
    # may allow it to be future proofed (but only for asset bundles
    # that contain this section - regular asset files omit this)

    (num_fields, string_table_len) = struct.unpack('<2I', file.read(8))

    file.seek(num_fields * 24, 1)
    string_table_raw = file.read(string_table_len).decode('ascii')
    string_table = string_table_raw.rstrip('\0').split('\0')
    # print('        "' + '"\n        "'.join(string_table) + '"')

    def pop_flags():
        popped_flags = flags_recursion.pop()
        if popped_flags & 0x4000:
            print('%*sAlign(4)' % (base_indentation + len(flags_recursion)*2 - 1, ''))
        if popped_flags & 0x8000:
            print('%*s' % (base_indentation + len(flags_recursion)*2, '}'))

    file.seek(8)
    last_level = 0
    base_indentation = 25
    flags_recursion = []
    is_array_len = False
    for idx in range(num_fields):
        (u0, z1, level, is_array, type_id, name_id, field_size, idx2, flags) = struct.unpack('''<
          B   B      B   B     I   I           i     I      I''', file.read(24))

        while len(flags_recursion) > level:
            pop_flags()

        if type_id & 0x80000000:
            type_name = type_map.get(type_id, '0x%08x' % type_id)
        else:
            type_name = string_table_raw[type_id:type_id+string_table_raw[type_id:].find('\0')]

        if name_id & 0x80000000:
            member_name = name_map.get(name_id, '') # '0x%08x' % name_id)
        else:
            member_name = string_table_raw[name_id:name_id+string_table_raw[name_id:].find('\0')]

        align = flags & 0x4000 # Aligns when object is popped
        scope = flags & 0x8000 and ' {' or ''
        # flags & 0x1 seems to indicate it is part of a string - the array, int
        # length, or chars

        if len(flags_recursion) <= level:
            flags_recursion += [0] * (level - len(flags_recursion) + 1)
        flags_recursion[level] = flags

        print('%i %8x %2i 0x%06x %*s %s%s %s%s%s' %
               (u0, name_id, field_size, flags,
                   level*2, "",
                   is_array_len and '[ ' or '',
                   type_name,
                   member_name,
                   is_array_len and ' ]' or '',
                   scope))

        is_array_len = is_array

        assert(u0 in (1, 2)) # SerializedShaderState and SerializedSubProgram are 2, everything else is 1
        assert(z1 == 0) # Maybe part of u0?
        assert(is_array in (0, 1))
        assert(idx2 == idx)
        assert(flags & 0x0080c001 == flags)

    while flags_recursion:
        pop_flags()

def dump_embedded_type_info(in_file, type_id, type_uuid):
    # Dumping this in a raw binary format in case we find a mistake in our
    # decoder, so we still have the original description to decode.
    filename = 'unity_types/{}-{:08x}{:08x}{:08x}{:08x}'.format(*([type_id] + list(type_uuid)))
    data = io.BytesIO()
    data.write(in_file.read(8))
    (num_fields, string_table_len) = struct.unpack('<2I', data.getvalue())
    data.write(in_file.read(num_fields * 24 + string_table_len))

    print('        Dumping raw type info to %s...' % filename)
    if not os.path.isdir('unity_types'):
        os.mkdir('unity_types')
    with open(filename, 'wb') as out_file:
        out_file.write(data.getvalue())

    data.seek(0)
    decode_embedded_type_info(data)

# FIXME: Not all resource types have a filename!
def get_resource_name(file, base_offset, offset):
    saved_off = file.tell()

    file.seek(base_offset+offset)
    (name_len,) = struct.unpack('<I', file.read(4))
    ret = file.read(name_len)

    file.seek(saved_off)

    return ret

def get_extraction_path(asset_file, resource_name, resource_offset, extension):
    (dir, ext) = os.path.splitext(os.path.basename(asset_file.name))

    if not os.path.isdir('extracted'):
        os.mkdir('extracted')

    dir = 'extracted/' + dir
    if not os.path.isdir(dir):
        os.mkdir(dir)

    if resource_name:
        filename = '{}.{}'.format(resource_name, extension)
    else:
        filename = '0x{:08x}.{}'.format(resource_offset, extension)
    return os.path.join(dir, filename)

def align(file, alignment):
    off = file.tell()
    mod = off % alignment
    if mod == 0:
        return
    file.seek(alignment - mod, 1)

def repeat_extend(s, target_length):
    '''
    Expands (or shrinks) a string to an arbitrary length by repeating it.
    '''
    return s*(target_length // len(s)) + s[:target_length % len(s)]

# http://cyan4973.github.io/lz4/lz4_Block_format.html
# https://en.wikipedia.org/wiki/LZ4_(compression_algorithm)
# Plus a bunch of experimentation and comparing against the result of reference
# implementations, because while the documentation is relatively clear, it
# fails to unambiguously describe the entire algorithm.
#
# Not using any of the the available Python libraries to do this because the
# format isn't exactly what the first one I looked at expected (though we could
# potentially munge it to match), but mostly because they all include a C
# module which complicates installation on Windows.
def lz4_decompress(file, decompressed_size):
    decoded = bytearray()

    while True:
        (token,) = struct.unpack('B', file.read(1))

        num_literals = token >> 4
        if num_literals == 15:
            while True:
                (tmp,) = struct.unpack('B', file.read(1))
                num_literals += tmp
                if tmp != 255:
                    break
        tmp = file.read(num_literals)
        assert(len(tmp) == num_literals)
        decoded.extend(tmp)

        if len(decoded) == decompressed_size:
            return decoded
        assert(len(decoded) < decompressed_size)

        (match_offset,) = struct.unpack('<H', file.read(2))
        match_len = (token & 0xf) + 4
        if match_len == 19:
            while True:
                (tmp,) = struct.unpack('B', file.read(1))
                match_len += tmp
                if tmp != 255:
                    break

        assert(match_offset != 0)
        assert(match_offset <= len(decoded))

        # len()- is necessary here since match_offset may equal match_len
        tmp = decoded[-match_offset : len(decoded) - match_offset + match_len]
        tmp = repeat_extend(tmp, match_len)
        decoded.extend(tmp)

def unity_53_or_higher(unity_version):
    '''
    Shader asset format changed in this version to use LZ4 compression and a
    binary format packed after the Unity shader metadata (which is now of very
    little use, though may still be useful to identify shadow casters). As far
    as I can tell they neglected to bump the file version or add any flags to
    signify this change, and some old files contain stack garbage that might be
    mistaken for compressed data, so check the Unity version string.
    '''
    (major, minor, point) = unity_version.split(b'.')
    return int(major) > 5 or (int(major) == 5 and int(minor) >= 3)

def extract_raw(file, base_offset, offset, size, unity_version, file_version, type_uuid, extension='raw'):
    '''
    Usually unused, but useful to hook up for debugging purposes
    '''
    saved_off = file.tell()
    try:
        file.seek(base_offset+offset)
        path = get_extraction_path(file, None, base_offset + offset, extension)

        print('Dumping {}...'.format(repr(path)))
        with open(path, 'wb') as out:
            out.write(file.read(size))

    except:
        file.seek(saved_off)
        raise
    else:
        file.seek(saved_off)

def extract_shader(file, base_offset, offset, size, unity_version, file_version, type_uuid):
    if file_version >= 17:
        # All textual metadata has been replaced by a custom binary format,
        # which we leave for extract_unity55_shaders to deal with. Just extract
        # the raw shader asset instead. This binary format can change of
        # course, and is only self-describing in asset bundles that we can't
        # rely on, so we write the type uuid to the filename for the next
        # script to pick up:
        extension = '{:08x}{:08x}{:08x}{:08x}.shader.raw'.format(*type_uuid)
        return extract_raw(file, base_offset, offset, size, unity_version, file_version, type_uuid, extension)

    saved_off = file.tell()
    try:
        file.seek(base_offset+offset)

        (name_len,) = struct.unpack('<I', file.read(4))
        resource_name = file.read(name_len).decode('ascii')
        path = get_extraction_path(file, resource_name, base_offset + offset, 'shader')

        align(file, 4)
        (shader_len,) = struct.unpack('<I', file.read(4))

        print('Extracting {}...'.format(repr(path)))
        with open(path, 'wb') as out:
            out.write(file.read(shader_len))

        if unity_53_or_higher(unity_version):
            align(file, 4)
            (zero, decompressed_size, compressed_size) = struct.unpack('<III', file.read(12))
            assert(zero == 0)
            print("Decompressed size: {}, Compressed size: {}".format(decompressed_size, compressed_size))
            if decompressed_size and compressed_size:
                decompressed = lz4_decompress(file, decompressed_size)
                print('Extracting {}.decompressed...'.format(repr(path)))
                with open(path + '.decompressed', 'wb') as out:
                    out.write(decompressed)

    except:
        file.seek(saved_off)
        raise
    else:
        file.seek(saved_off)

# Shader (Type 48) known UUIDs - this tells us when the shader file format has
# changed. Asset Bundles include a data structure self-describing the formats
# these correspond to (in case they are opened by older/other Unity versions I
# presume), but regular asset files assume that Unity already knows the format.
#
# Unity version from exe on left (excluding build number), Unity version in
# asset file in brackets.
#
# 5.1.2 (5.1.0b5):        82cbe6ba 9f2fd496 d8e14747 a764dc4f
# 5.1.5 (5.1.0b5):        82cbe6ba 9f2fd496 d8e14747 a764dc4f
# 5.2.2 (5.2.1p1):        82cbe6ba 9f2fd496 d8e14747 a764dc4f
# 5.2.3 (5.2.1p3):        82cbe6ba 9f2fd496 d8e14747 a764dc4f
# 5.3.2 (5.3.0p1):        313f624e 8093f279 302b3b65 25bbb83a
# 5.3.7 (5.3.6p2):        313f624e 8093f279 302b3b65 25bbb83a
# 5.4.0 (5.4.0f2):        d50ed133 62e98df8 096b2f73 5131fce5
# 5.4.4 (5.4.0p4):        d50ed133 62e98df8 096b2f73 5131fce5
# 5.5.0 (5.5.0f2):        4496e93f 21792521 04401c8d da0a1751
# 5.5.2 (5.5.0p3):        4496e93f 21792521 04401c8d da0a1751
# 5.6.0 (5.6.0f1):        a70f7abc 6586fb35 b3a0641a a81e9375
# 5.6.1 (5.6.0p2):        a70f7abc 6586fb35 b3a0641a a81e9375
# 5.6.2 (5.6.1p1):        a70f7abc 6586fb35 b3a0641a a81e9375
# 2017.1.0 (2017.1.0f1):  5d6434c0 4f879e08 410f5935 5c6dfe0a
# 2017.1.1 (2017.1.0f1):  5d6434c0 4f879e08 410f5935 5c6dfe0a
# 2017.2
# 2017.3.0 (2017.3.0b10): 266d5311 3fa30d2b 858f2768 f92eaa14

extractors = {
    # 48: extract_raw,
    48: extract_shader,
    # TODO: 142: extract_asset_bundle... yeah, looks like an asset file can contain an asset bundle, which contains more asset files...
}

def extract_resource(file, base_offset, offset, size, type, type_uuid, unity_version, file_version):
    if type in extractors:
        extractors[type](file, base_offset, offset, size, unity_version, file_version, type_uuid)

def parse_version_9(file, version):
    (data_off, u1) = struct.unpack('>2I', file.read(8))

    print("Data offset: 0x{0:x} ({0})".format(data_off))
    assert(data_off >= 4096)

    # print("Unknown1: 0x{0:08x} ({0})".format(u1))
    assert(u1 == 0)

    unity_version = read_cstring(file)
    print("Unity version: {0}".format(unity_version.decode('ascii')))

    (u2, u3, u4, num_resources) = struct.unpack('<4I', file.read(16))
    print("Unknown2: 0x{0:08x} ({0})".format(u2))
    # print("Unknown3: 0x{0:08x} ({0})".format(u3))
    assert(u3 == 0)
    # print("Unknown4: 0x{0:08x} ({0})".format(u4))
    assert(u4 == 0)

    print("Num resources: {}".format(num_resources))
    for i in range(num_resources):
        (id, offset, size, type1, type2) = struct.unpack('<IIIiI', file.read(20))
        print("   Resource {}: offset 0x{:08x}, size {}, type(?) {}, type: {}".format(id, offset, size, type1, type2))
        # assert(id == i+1) - no

        extract_resource(file, data_off, offset, size, type2, None, unity_version, version)

def parse_version_14(file, version):
    (data_off, u1) = struct.unpack('>2I', file.read(8))

    print("Data offset: 0x{0:x} ({0})".format(data_off))
    assert(data_off >= 4096)

    # print("Unknown1: 0x{0:08x} ({0})".format(u1))
    # Non-zero in version 8
    assert(u1 == 0)

    unity_version = read_cstring(file)
    print("Unity version: {0}".format(unity_version.decode('ascii')))

    (u2, u3, unknown_table_len, u6, u7) = struct.unpack('<IBHBB', file.read(9))
    print("Type table length: {0}".format(unknown_table_len))

    # Not sure what this value represents, but it seems to be consistent within
    # a single project. Seen 0x5 in Ori, 0x13 in Unity 5.0.0 personal (Viking sample)
    print("Unknown value: 0x{:02x}".format(u2))
    assert(u2 == 0x5 or u2 == 0x13)

    assert(u3 == 0)
    assert(u6 == 0)
    assert(u7 == 0)

    for i in range(unknown_table_len):
        (id,) = struct.unpack('<i', file.read(4))

        if (id < 0):
            u = struct.unpack('>8I', file.read(32))
            print(("   {:3}: {:3}" + " {:08x}" * 8).format(*([i, id] + list(u))))
        else:
            u = struct.unpack('>4I', file.read(16))
            print(("   {:3}: {:3}" + " {:08x}" * 4).format(*([i, id] + list(u))))

    (num_resources, u1, u2, u3) = struct.unpack('<I3B', file.read(7))
    # FIXME: This is very likely supposed to be align(file, 4) like in v17 - needs testing
    assert(u1 == 0)
    assert(u2 == 0)
    assert(u3 == 0)

    print("Num resources: {}".format(num_resources))
    for i in range(num_resources):
        (id, u1, offset, size, type1, type2, type3) = struct.unpack('<4IiHh', file.read(24))
        name = get_resource_name(file, data_off, offset)
        print("   Resource {}: offset: 0x{:08x}, size: {:6}, {}, {}, {}, {}".format(id, offset, size, type1, type2, type3, name))
        assert(u1 == 0)

        extract_resource(file, data_off, offset, size, type2, None, unity_version, version)

def parse_version_15(file, version):
    # Looks almost identical to version 14, but each TOC entry has extra padding
    # TODO: Refactor common parts
    (data_off, u1) = struct.unpack('>2I', file.read(8))

    print("Data offset: 0x{0:x} ({0})".format(data_off))
    assert(data_off >= 4096)

    # print("Unknown1: 0x{0:08x} ({0})".format(u1))
    # Non-zero in version 8
    assert(u1 == 0)

    unity_version = read_cstring(file)
    print("Unity version: {0}".format(unity_version.decode('ascii')))

    (u2, u3, unknown_table_len, u6, u7) = struct.unpack('<IBHBB', file.read(9))
    print("Type table length: {0}".format(unknown_table_len))

    # Not sure what this value represents, but it seems to be consistent within
    # a single project. Seen 0x5 in Ori, 0x13 in Unity 5.0.0 personal (Viking sample)
    # FIXME: This failed on Mind Unleashed & Stealth Labyrinth (u2 == 0x500),
    # but these need more work to parse
    print("Unknown value: 0x{:02x}".format(u2))
    assert(u2 == 0x5 or u2 == 0x13)

    assert(u3 == 0)
    assert(u6 == 0)
    assert(u7 == 0)

    for i in range(unknown_table_len):
        (id,) = struct.unpack('<i', file.read(4))

        if (id < 0):
            u = struct.unpack('>8I', file.read(32))
            print(("   {:3}: {:3}" + " {:08x}" * 8).format(*([i, id] + list(u))))
        else:
            u = struct.unpack('>4I', file.read(16))
            print(("   {:3}: {:3}" + " {:08x}" * 4).format(*([i, id] + list(u))))

    (num_resources, u1, u2, u3) = struct.unpack('<I3B', file.read(7))
    # FIXME: This is very likely supposed to be align(file, 4) like in v17 - needs testing
    assert(u1 == 0)
    assert(u2 == 0)
    assert(u3 == 0)

    print("Num resources: {}".format(num_resources))
    for i in range(num_resources):
        (id, u1, offset, size, type1, type2, type3, u2) = struct.unpack('<4IiHhI', file.read(28))
        name = get_resource_name(file, data_off, offset)
        print("   Resource {}: offset: 0x{:08x}, size: {:6}, {}, {}, {}, {}, u2: 0x{:x}".format(id, offset, size, type1, type2, type3, name, u2))
        assert(u1 == 0)
        # assert(u2 == 0) Last resource was non-zero. Possibly followed by another table?

        extract_resource(file, data_off, offset, size, type2, None, unity_version, version)

def parse_version_17(file, version):
    # Looks almost identical to version 14, but each TOC entry has extra padding
    # TODO: Refactor common parts
    (data_off, u1) = struct.unpack('>2I', file.read(8))

    print("Data offset: 0x{0:x} ({0})".format(data_off))
    assert(data_off >= 4096)

    # print("Unknown1: 0x{0:08x} ({0})".format(u1))
    # Non-zero in version 8
    assert(u1 == 0)

    unity_version = read_cstring(file)
    print("Unity version: {0}".format(unity_version.decode('ascii')))

    (u2, embedded, type_table_len, u6, u7) = struct.unpack('<IBHBB', file.read(9))
    print("Type table length: {0}".format(type_table_len))

    # Not sure what this value represents, but it seems to be consistent within
    # a single project. Seen 0x5 in Ori, 0x13 in Unity 5.0.0 personal (Viking sample)
    print("Unknown value: 0x{:02x}".format(u2))
    print("Has data structure descriptions embedded in type table: %i" % embedded)
    assert(u2 == 0x5 or u2 == 0x13)

    assert(u6 == 0)
    assert(u7 == 0)

    type_uuids = []
    types = set()

    for i in range(type_table_len):
        # neovad added 00 FF FF or 00 00 00 pattern (3 byte) in 17 version
        # after id as 4/8 I switch.
        (id, b1, b2) = struct.unpack('<iBh', file.read(7))
        assert(b1 == 0)

        # This UUID is noteworthy that each type always maps to the same hash
        # in a given Unity version, though the hash may change between
        # versions. extract_unity55_shaders now uses this to distinguish
        # between different variations in the new shader binary format:
        u = struct.unpack('>4I', file.read(16))
        types.add(id)
        type_uuids.append((id, u))

        # Some types have larger uuids than others, indicated by b2:
        if b2 >= 0: # Changed since v15
            u1 = struct.unpack('>4I', file.read(16))
            print(("   {:3}: {:3} {:2}" + " {:08x}" * 8).format(*([i, id, b2] + list(u) + list(u1))))
        else:
            print(("   {:3}: {:3} {:2}" + " {:08x}" * 4).format(*([i, id, b2] + list(u))))

            if id == 114 and b2 == -1 and u == (0, 0, 0, 0):
                # Seen in LisBtS DLC/E2/e2_s01_d_loc.bytes in contained file
                # "BuildPlayer-E2_S01D_BlackwellLot". Has numerous type 114
                # entries, some with b2 positive and valid 32 byte hashes,
                # others with b2 == -1, but still 32 byte hashes, all zero.
                # Not positive of the correct way to detect this - zero hash,
                # negative b2 following other positive b2s for the same type,
                # a special case for this specific combination, or something
                # else? For now being as specific as possible.
                u = struct.unpack('>4I', file.read(16))
                assert(u == (0, 0, 0, 0))
                print(("        !!!!!!" + " {:08x}" * 4).format(*list(u)))

        if embedded:
            if args.dump_type_info:
                dump_embedded_type_info(file, id, u)
            else:
                print('        Skipping data structure description...')
                (num_fields, string_table_len) = struct.unpack('<2I', file.read(8))
                file.seek(num_fields * 24 + string_table_len, 1)

    if set(extractors.keys()).intersection(types) == set():
        print()
        print('Bailing: Type table indicates that no assets of desired types are present')
        return

    (num_resources,) = struct.unpack('<I', file.read(4))
    align(file, 4)

    print("Num resources: {}".format(num_resources))
    for i in range(num_resources):
        (id, offset, size, type_idx) = struct.unpack('<Q3I', file.read(20))
        name = get_resource_name(file, data_off, offset)
        (type2, type_uuid) = type_uuids[type_idx]
        print("   Resource {}: offset: 0x{:08x}, size: {:6}, {}, type: {}".format(id, offset, size, name, type2))
        extract_resource(file, data_off, offset, size, type2, type_uuid, unity_version, version)

def unsupported_version(file, version):
    print("Unsupported file version {}".format(version))

parsers = {
    8: unsupported_version,
    9: parse_version_9,   # Unity ..., 4.3, 4.4, 4.5, 4.6, ...
    14: parse_version_14, # Unity ...
    15: parse_version_15, # Unity ..., 5.1, 5.2, 5.3, 5.4
    17: parse_version_17, # Unity 5.5, 5.6, ...
}

def analyse(file):
    (header_len, file_len, version) = struct.unpack('>3I', file.read(12))

    # Seems to be 18 bytes larger than this, if not more:
    print("Header len (?): {0} (0x{0:08x})".format(header_len))
    # file.seek(header_len + 18)
    # print(repr(file.read(16)))

    # print("File size: {0} bytes".format(file_len))
    try:
        assert(os.fstat(file.fileno()).st_size == file_len)
    except io.UnsupportedOperation:
        pass

    # 8 in Creavures, 9 in most Unity 4 games, 14 in Ori (Unity 5)
    print("File Version: {0}".format(version))
    parsers.get(version, unsupported_version)(file, version)

def parse_args():
    global args
    parser = argparse.ArgumentParser(description = 'Unity Asset Extractor')
    parser.add_argument('assets', nargs='*',
            help='List of Unity asset files to parse')
    parser.add_argument('--dump-type-info', action='store_true',
            help='Dump self-describing type info found in Unity Asset Bundles')
    parser.add_argument('--decode-type-info',
            help='Decodes a previously extracted type info file')
    args = parser.parse_args()

def main():
    parse_args()

    if args.decode_type_info:
        decode_embedded_type_info(open(args.decode_type_info, 'rb'))

    # Windows command prompt passes us a literal *, so expand any that we were passed:
    import glob
    f = []
    for file in args.assets:
        if '*' in file:
            f.extend(glob.glob(file))
        else:
            f.append(file)

    for file in f:
        print('Analysing %s...' % file)
        analyse(open(file, 'rb'))
        print()


if __name__ == '__main__':
    main()

# vi:ts=4:sw=4:et
