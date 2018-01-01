#!/usr/bin/env python3

import sys, os, struct, io
import unity_asset_extractor
from unity_asset_extractor import lz4_decompress

class BlockStream(object):
    def __init__(self, name, data_header, file):
        (self.num_blocks,) = struct.unpack('>I', data_header.read(4))
        self.blocks = []
        self.blocks_start = file.tell()
        self.name = name
        self.file = file
        self.cache = {}

        print('Number of blocks: %i' % self.num_blocks)
        for i in range(self.num_blocks):
            (decompressed_size, compressed_size, flags) = struct.unpack('>IIH', data_header.read(10))
            self.blocks.append((decompressed_size, compressed_size, flags))

        self.seek(0)

    def activate_block(self):
        try:
            self.block = self.cache[self.block_idx]
        except KeyError:
            print('BlockStream %s: Reading block %i/%i' % (self.name, self.block_idx + 1, self.num_blocks))
        else:
            # print('BlockStream %s: Using block cache %i/%i' % (self.name, self.block_idx + 1, self.num_blocks))
            return

        try:
            (decompressed_size, compressed_size, flags) = self.blocks[self.block_idx]
        except IndexError:
            self.block_idx = None
            self.block = io.BytesIO()
            print('BlockStream %s: EOF' % self.name)
            return

        self.file.seek(self.blocks_start + self.compressed_pos)
        self.block = io.BytesIO(self.file.read(compressed_size))

        if flags & 0x3f == 0:
            pass
        elif flags & 0x3f == 0x3:
            self.block = io.BytesIO(lz4_decompress(self.block, decompressed_size))
        else:
            assert(False) # FIXME: Unsupported compression scheme

        self.cache[self.block_idx] = self.block

    def next_block(self):
        (decompressed_size, compressed_size, flags) = self.blocks[self.block_idx]
        self.decompressed_pos += decompressed_size
        self.compressed_pos += compressed_size
        self.block_idx += 1
        self.activate_block()

    def read(self, size):
        buf = self.block.read(size)
        while len(buf) < size and self.block_idx is not None:
            self.next_block()
            buf += self.block.read(size - len(buf))
        return buf

    def seek(self, pos, whence=0):
        if whence == 0:
            pass
        elif whence == 1:
            self.read(pos) # FIXME: Skip reading
            return
        else:
            raise io.UnsupportedOperation()

        self.decompressed_pos = 0
        self.compressed_pos = 0
        for self.block_idx, (decompressed_size, compressed_size, flags) in enumerate(self.blocks):
            if self.decompressed_pos + decompressed_size > pos:
                break
            self.decompressed_pos += decompressed_size
            self.compressed_pos += compressed_size

        self.activate_block()
        self.block.seek(pos - self.decompressed_pos)

    def tell(self):
        return self.decompressed_pos + self.block.tell()

class OffsetIO(object):
    def __init__(self, name, buf, offset, size):
        self.name = name
        self.buf = buf
        self.offset = offset
        self.size = size
        self.seek(0)

    def read(self, size=-1):
        # FIXME: Prevent read past end of self.size
        return self.buf.read(size)

    def seek(self, target, whence=0):
        if whence == 0:
            return self.buf.seek(self.offset + target)
        return self.buf.seek(target, whence)

    def tell(self):
        return self.buf.tell() - self.offset

    def fileno(self):
        raise io.UnsupportedOperation()

def _read_cstring(file, size=None):
    s = b''
    while True:
        c = file.read(1)
        if c == b'':
            raise EOFError()
        if c == b'\0':
            return s
        if size is not None and len(s) >= size:
            raise IndexError()
        s += c

def read_cstring(file, size=None):
    return _read_cstring(file, size=size).decode('ascii')

def analyse(file):
    try:
        magic = _read_cstring(file, 7)
    except Exception as e:
        print('%s occurred while looking for UnityFS signature' % e.__class__.__name__)
        return
    if magic != b'UnityFS':
        print('Not a UnityFS file')
        return

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

    block_stream = BlockStream(file.name, data_header, file)

    (num_files,) = struct.unpack('>I', data_header.read(4))
    print('Number of files: %i' % num_files)
    for i in range(num_files):
        (offset, size, flags) = struct.unpack('>QQI', data_header.read(20))
        name = read_cstring(data_header)
        print(' File %i: 0x%016x %10u 0x%08x "%s"' % (i, offset, size, flags, name))

        # Flag 0x4 appears to signify that the file is an asset container,
        # which we will analyse using unity_asset_extractor. Not 100% positive
        # that is correct, but seems to be the case on the files I've looked at
        # so far.
        if flags & 0x4:
            asset_stream = OffsetIO(name, block_stream, offset, size)
            unity_asset_extractor.analyse(asset_stream)
        else:
            print('  Skipping analysis due to missing flag 0x4')

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
