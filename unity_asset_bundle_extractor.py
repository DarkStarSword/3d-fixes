#!/usr/bin/env python3

import sys, os, struct, io
import unity_asset_extractor
from unity_asset_extractor import lz4_decompress

def read_cstring(file):
    s = b''
    while True:
        c = file.read(1)
        if c == b'\0':
            return s.decode('ascii')
        s += c

def analyse(file):
    magic = read_cstring(file)
    assert(magic == 'UnityFS')

    (file_version,) = struct.unpack('>I', file.read(4))
    assert(file_version == 6)

    compat_version = read_cstring(file)
    created_version = read_cstring(file)
    print('Bundle compatible with Unity %s' % compat_version)
    print('Bundle created with Unity %s' % created_version)

    (file_size, compressed_size, decompressed_size, flags) = struct.unpack('>Q3I', file.read(20))
    assert(os.fstat(file.fileno()).st_size == file_size)
    print('file size: %i' % file_size)
    print('compressed data header size: %i' % compressed_size)
    print('data header size: %i' % decompressed_size)
    print('flags: 0x%08x' % flags)

    data_header = file.read(compressed_size)
    if flags & 0x3f == 0x0:
        pass
    elif flags & 0x3f == 0x3:
        data_header = io.BytesIO(lz4_decompress(io.BytesIO(data_header), decompressed_size))
    else:
        assert(False) # FIXME: Unsupported compression scheme

    assert(data_header.read(16) == b'\0' * 16)

    decompressed = b''

    (num_blocks,) = struct.unpack('>I', data_header.read(4))
    print('Number of blocks: %i' % num_blocks)
    for i in range(num_blocks):
        (decompressed_size, compressed_size, flags) = struct.unpack('>IIH', data_header.read(10))
        print('Decompressing block %i/%i' % (i+1, num_blocks))
        # print('  decompressed size: %i' % decompressed_size)
        # print('  compressed size: %i' % compressed_size)
        # print('  flags: 0x%04x' % flags)
        block = file.read(compressed_size)
        if flags & 0x3f == 0x0:
            pass
        elif flags & 0x3f == 0x3:
            block = lz4_decompress(io.BytesIO(block), decompressed_size)
        else:
            assert(False) # FIXME: Unsupported compression scheme
        decompressed += block

    (num_files,) = struct.unpack('>I', data_header.read(4))
    print('Number of files: %i' % num_files)
    for i in range(num_files):
        (offset, size, flags) = struct.unpack('>QQI', data_header.read(20))
        name = read_cstring(data_header)
        print(' File %i: 0x%016x %10u 0x%08x "%s"' % (i, offset, size, flags, name))
        stream = io.BytesIO(decompressed[offset:offset+size])
        stream.name = name
        unity_asset_extractor.analyse(stream)

    assert(data_header.read(1) == b'')

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
