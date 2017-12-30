#!/usr/bin/env python3

import sys, os, struct, itertools
import unity_asset_extractor

def read_cstring(file):
    s = b''
    while True:
        c = file.read(1)
        if c == b'\0':
            return s
        s += c

def analyse(file):
    magic = read_cstring(file)
    assert(magic == b'UnityFS')

    (file_version,) = struct.unpack('>I', file.read(4))
    assert(file_version == 6)

    compat_version = read_cstring(file).decode('ascii')
    created_version = read_cstring(file).decode('ascii')
    print('Bundle compatible with Unity %s' % compat_version)
    print('Bundle created with Unity %s' % created_version)

    (zero, file_size, compressed_size, decompressed_size, header_size, flags) = struct.unpack('>6I', file.read(24))
    assert(zero == 0)
    assert(os.fstat(file.fileno()).st_size == file_size)
    print('compressed size: %i' % compressed_size) # data start or TOC len?
    print('decompressed size: %i' % decompressed_size)
    print('header size: %i' % header_size)
    assert(header_size == 67)
    print('flags: 0x%08x' % flags)
    assert(flags in (0x1d000100, 0x1e000100))

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
