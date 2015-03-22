#!/usr/bin/env python3

import sys, os, struct, itertools

# FIXME: Not all resource types have a filename!
def get_resource_name(file, base_offset, offset):
    saved_off = file.tell()

    file.seek(base_offset+offset)
    (name_len,) = struct.unpack('<I', file.read(4))
    ret = file.read(name_len)

    file.seek(saved_off)

    return ret

def get_extraction_path(asset_file, resource_name, extension):
    (dir, ext) = os.path.splitext(os.path.basename(asset_file.name))

    if not os.path.isdir('extracted'):
        os.mkdir('extracted')

    dir = 'extracted/' + dir
    if not os.path.isdir(dir):
        os.mkdir(dir)

    filename = '{}.{}'.format(resource_name, extension)
    return os.path.join(dir, filename)

def align(file, alignment):
    off = file.tell()
    mod = off % alignment
    if mod == 0:
        return
    file.seek(alignment - mod, 1)

def extract_shader(file, base_offset, offset, size):
    saved_off = file.tell()
    try:
        file.seek(base_offset+offset)

        (name_len,) = struct.unpack('<I', file.read(4))
        resource_name = file.read(name_len).decode('ascii')
        path = get_extraction_path(file, resource_name, 'shader')

        align(file, 4)
        (shader_len,) = struct.unpack('<I', file.read(4))

        print('Extracting {}...'.format(repr(path)))
        with open(path, 'wb') as out:
            out.write(file.read(shader_len))

    except:
        file.seek(saved_off)
        raise
    else:
        file.seek(saved_off)

extractors = {
    48: extract_shader,
}

def extract_resource(file, base_offset, offset, size, type):
    if type in extractors:
        extractors[type](file, base_offset, offset, size)

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

        extract_resource(file, data_off, offset, size, type2)

def parse_version_14(file, version):
    (data_off, u1) = struct.unpack('>2I', file.read(8))

    print("Data offset: 0x{0:x} ({0})".format(data_off))
    assert(data_off >= 4096)

    # print("Unknown1: 0x{0:08x} ({0})".format(u1))
    # Non-zero in version 8
    assert(u1 == 0)

    (unity_version, ) = struct.unpack('8s', file.read(8))
    print("Unity version: {0}".format(unity_version.decode('ascii').rstrip('\0')))

    (u2, u3, unknown_table_len, u5, u6, u7) = struct.unpack('<IBBBBB', file.read(9))
    print("Unknown table length: {0}".format(unknown_table_len))
    assert(u2 == 5)
    assert(u3 == 0)
    assert(u5 == 0)
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
    assert(u1 == 0)
    assert(u2 == 0)
    assert(u3 == 0)

    print("Num resources: {}".format(num_resources))
    for i in range(num_resources):
        (id, u1, offset, size, type1, type2, type3) = struct.unpack('<4IiHh', file.read(24))
        name = get_resource_name(file, data_off, offset)
        print("   Resource {}: offset: 0x{:08x}, size: {:6}, {}, {}, {}, {}".format(id, offset, size, type1, type2, type3, name))
        assert(u1 == 0)

        extract_resource(file, data_off, offset, size, type2)

def unsupported_version(file, version):
    print("Unsupported file version {}".format(version))

parsers = {
    8: unsupported_version,
    9: parse_version_9,
    14: parse_version_14,
}

def analyse(file):
    (header_len, file_len, version) = struct.unpack('>3I', file.read(12))

    # Seems to be 18 bytes larger than this, if not more:
    print("Header len (?): {0} (0x{0:08x})".format(header_len))
    # file.seek(header_len + 18)
    # print(repr(file.read(16)))

    # print("File size: {0} bytes".format(file_len))
    assert(os.fstat(file.fileno()).st_size == file_len)

    # 8 in Creavures, 9 in most Unity 4 games, 14 in Ori (Unity 5)
    print("File Version: {0}".format(version))
    parsers.get(version, unsupported_version)(file, version)

def main():
    for file in sys.argv[1:]:
        print('Analysing %s...' % file)
        analyse(open(file, 'rb'))
        print()


if __name__ == '__main__':
    main()

# vi:ts=4:sw=4:et
