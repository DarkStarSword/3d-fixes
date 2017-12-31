#!/usr/bin/env python3

import sys, os, struct, itertools, codecs, io

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

def extract_raw(file, base_offset, offset, size, unity_version, file_version, extension='raw'):
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

def extract_shader(file, base_offset, offset, size, unity_version, file_version):
    if file_version >= 17:
        # All textual metadata has been replaced by a custom binary format,
        # which we leave for extract_unity55_shaders to deal with. Just extract
        # the raw shader asset instead:
        return extract_raw(file, base_offset, offset, size, unity_version, file_version, 'shader.raw')

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

# Shader (Type 48) known UUIDs:
# 5.1.2 (5.1.0b5): 82cbe6ba 9f2fd496 d8e14747 a764dc4f
# 5.1.5 (5.1.0b5): 82cbe6ba 9f2fd496 d8e14747 a764dc4f
# 5.2.2 (5.2.1p1): 82cbe6ba 9f2fd496 d8e14747 a764dc4f
# 5.2.3 (5.2.1p3): 82cbe6ba 9f2fd496 d8e14747 a764dc4f
# 5.3.2 (5.3.0p1): 313f624e 8093f279 302b3b65 25bbb83a
# 5.3.7 (5.3.6p2): 313f624e 8093f279 302b3b65 25bbb83a
# 5.4.0 (5.4.0f2): d50ed133 62e98df8 096b2f73 5131fce5
# 5.4.4 (5.4.0p4): d50ed133 62e98df8 096b2f73 5131fce5
# 5.5.0 (5.5.0f2): 4496e93f 21792521 04401c8d da0a1751
# 5.5.2 (5.5.0p3): 4496e93f 21792521 04401c8d da0a1751
# 5.6.0 (5.6.0f1): a70f7abc 6586fb35 b3a0641a a81e9375
# 5.6.1 (5.6.0p2): a70f7abc 6586fb35 b3a0641a a81e9375
# 5.6.2 (5.6.1p1): a70f7abc 6586fb35 b3a0641a a81e9375

extractors = {
    # 48: extract_raw,
    48: extract_shader,
    # TODO: 142: extract_asset_bundle... yeah, looks like an asset file can contain an asset bundle, which contains more asset files...
}

def extract_resource(file, base_offset, offset, size, type, unity_version, file_version):
    if type in extractors:
        extractors[type](file, base_offset, offset, size, unity_version, file_version)

def parse_version_9(file, version):
    (data_off, u1) = struct.unpack('>2I', file.read(8))

    print("Data offset: 0x{0:x} ({0})".format(data_off))
    assert(data_off >= 4096)

    # print("Unknown1: 0x{0:08x} ({0})".format(u1))
    assert(u1 == 0)

    (unity_version, ) = struct.unpack('8s', file.read(8))
    print("Unity version: {0}".format(unity_version.decode('ascii').rstrip('\0')))

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

        extract_resource(file, data_off, offset, size, type2, unity_version, version)

def parse_version_14(file, version):
    (data_off, u1) = struct.unpack('>2I', file.read(8))

    print("Data offset: 0x{0:x} ({0})".format(data_off))
    assert(data_off >= 4096)

    # print("Unknown1: 0x{0:08x} ({0})".format(u1))
    # Non-zero in version 8
    assert(u1 == 0)

    (unity_version, ) = struct.unpack('8s', file.read(8))
    print("Unity version: {0}".format(unity_version.decode('ascii').rstrip('\0')))

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

        extract_resource(file, data_off, offset, size, type2, unity_version, version)

def parse_version_15(file, version):
    # Looks almost identical to version 14, but each TOC entry has extra padding
    # TODO: Refactor common parts
    (data_off, u1) = struct.unpack('>2I', file.read(8))

    print("Data offset: 0x{0:x} ({0})".format(data_off))
    assert(data_off >= 4096)

    # print("Unknown1: 0x{0:08x} ({0})".format(u1))
    # Non-zero in version 8
    assert(u1 == 0)

    (unity_version, ) = struct.unpack('8s', file.read(8))
    print("Unity version: {0}".format(unity_version.decode('ascii').rstrip('\0')))

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

        extract_resource(file, data_off, offset, size, type2, unity_version, version)

def parse_version_17(file, version):
    # Looks almost identical to version 14, but each TOC entry has extra padding
    # TODO: Refactor common parts
    (data_off, u1) = struct.unpack('>2I', file.read(8))

    print("Data offset: 0x{0:x} ({0})".format(data_off))
    assert(data_off >= 4096)

    # print("Unknown1: 0x{0:08x} ({0})".format(u1))
    # Non-zero in version 8
    assert(u1 == 0)

    (unity_version, ) = struct.unpack('8s', file.read(8))
    print("Unity version: {0}".format(unity_version.decode('ascii').rstrip('\0')))

    (u2, embedded, type_table_len, u6, u7) = struct.unpack('<IBHBB', file.read(9))
    print("Type table length: {0}".format(type_table_len))

    # Not sure what this value represents, but it seems to be consistent within
    # a single project. Seen 0x5 in Ori, 0x13 in Unity 5.0.0 personal (Viking sample)
    print("Unknown value: 0x{:02x}".format(u2))
    print("Has data structure descriptions embedded in type table: %i" % embedded)
    assert(u2 == 0x5 or u2 == 0x13)

    assert(u6 == 0)
    assert(u7 == 0)

    type_table = []

    for i in range(type_table_len):
        # neovad added 00 FF FF or 00 00 00 pattern (3 byte) in 17 version
        # after id as 4/8 I switch.
        (id, b1, b2) = struct.unpack('<iBh', file.read(7))
        assert(b1 == 0)

        type_table.append(id)

        # This hash(?) is noteworthy that each type always maps to the same
        # hash in a given Unity version, though the hash may change between
        # versions
        if b2 >= 0: # Changed since v15
            u = struct.unpack('>8I', file.read(32))
            print(("   {:3}: {:3} {:2}" + " {:08x}" * 8).format(*([i, id, b2] + list(u))))
        else:
            u = struct.unpack('>4I', file.read(16))
            print(("   {:3}: {:3} {:2}" + " {:08x}" * 4).format(*([i, id, b2] + list(u))))

        if embedded:
            (num_fields, string_table_len) = struct.unpack('<2I', file.read(8))
            if False:
                # TODO: Actually might want to parse this, as it describes the
                # data structure hardcoded in extract_unity55_shaders, which
                # may allow it to be future proofed (but only for asset bundles
                # that contain this section - regular asset files omit this)
                print('        Num fields: %i, String table len: %i' % (num_fields, string_table_len))
                for j in range(num_fields):
                    entry = file.read(24)
                    print('        ' + codecs.encode(entry, 'hex').decode('ascii'))
                string_table = file.read(string_table_len).decode('ascii')
                print('        "' + '"\n        "'.join(string_table.rstrip('\0').split('\0')) + '"')
            else:
                print('        Skipping data structure description...')
                file.seek(num_fields * 24 + string_table_len, 1)

    if set(extractors.keys()).intersection(type_table) == set():
        print()
        print('Bailing: Type table indicates that no assets of desired types are present')
        return

    (num_resources,) = struct.unpack('<I', file.read(4))
    align(file, 4)

    print("Num resources: {}".format(num_resources))
    for i in range(num_resources):
        (id, offset, size, type_idx) = struct.unpack('<Q3I', file.read(20))
        name = get_resource_name(file, data_off, offset)
        print("   Resource {}: offset: 0x{:08x}, size: {:6}, {}, type_idx: {}".format(id, offset, size, name, type_idx))
        type2 = type_table[type_idx]
        extract_resource(file, data_off, offset, size, type2, unity_version, version)

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

def main():

    # Windows command prompt passes us a literal *, so expand any that we were passed:
    import glob
    f = []
    for file in sys.argv[1:]:
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
