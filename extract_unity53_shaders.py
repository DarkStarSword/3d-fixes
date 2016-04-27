#!/usr/bin/env python3

import sys, os, argparse, glob, struct
import extract_unity_shaders

def align(file, alignment):
    off = file.tell()
    mod = off % alignment
    if mod == 0:
        return
    file.seek(alignment - mod, 1)

def extract_shader_at(file, offset, size):
    saved_offset = file.tell()
    file.seek(offset)
    try:
        (u1, u2, u3, u4, u5, num_keywords) = struct.unpack('<6I', file.read(24))
        print('  u1: {0} (0x{0:08x})'.format(u1))
        assert(u1 == 0x0c02c8a6)
        print('  u2: {0} (0x{0:08x})'.format(u2)) # 15, 16, 17, 18... shader type? at a guess, 17=vs? 15=ps?
        print('  u3: {0} (0x{0:08x})'.format(u3)) # Anything between 1 and 94?
        print('  u4: {0} (0x{0:08x})'.format(u4)) # Anything between 0 and 9?, sometimes 0xffffffff
        print('  u5: {0} (0x{0:08x})'.format(u5)) # usually 0, sometimes 1?, sometimes 0xffffffff
        print('  num_keywords: {0} (0x{0:08x})'.format(num_keywords))

        for i in range(num_keywords):
            (keyword_len,) = struct.unpack('<I', file.read(4))
            keyword = file.read(keyword_len)
            print('    Keyword %i: "%s"' % (i, keyword.decode('ascii')))
            align(file, 4)

        (shader_size, u8, u9) = struct.unpack('<2IB', file.read(9))
        print('  shader size: {0} (0x{0:08x})'.format(shader_size))
        print('  u8: {0} (0x{0:08x})'.format(u8)) # Looks like flags of some sort?
        print('  u9: {0} (0x{0:02x})'.format(u9)) # Usually 0, sometimes 2? 254

        shader = file.read(shader_size)
        # TODO: DX9
        hash = '%016x' % extract_unity_shaders.fnv_3Dmigoto_shader(shader)
        path = '%s--s.bin' % hash
        print('Extracting %s...' % path)
        with open(path, 'wb') as out:
            out.write(shader)

        remaining = size - (file.tell() - offset)
        print('  Remaining %i bytes' % remaining)
        print(file.read(remaining))
        print()

    except:
        file.seek(saved_offset)
        raise
    else:
        file.seek(saved_offset)

def parse_unity53_shader(file):
    (num_shaders,) = struct.unpack('<I', file.read(4))
    print('Num shaders: %i' % num_shaders)
    for i in range(num_shaders):
        (offset, size) = struct.unpack('<II', file.read(8))
        print('Shader %i offset: %i, size: %i' % (i, offset, size))
        extract_shader_at(file, offset, size)

def parse_args():
    global args
    parser = argparse.ArgumentParser(description = 'Unity 5.3 Shader Extractor')
    parser.add_argument('shaders', nargs='+',
            help='List of compiled Unity shader files to parse')
    args = parser.parse_args()

def main():
    parse_args()

    # Windows command prompt passes us a literal *, so expand any that we were passed:
    import glob
    f = []
    for file in args.shaders:
        if '*' in file:
            f.extend(glob.glob(file))
        else:
            f.append(file)
    args.shaders = f

    for filename in args.shaders:
        print('Processing %s...' % filename)
        parse_unity53_shader(open(filename, 'rb'))
        print()

if __name__ == '__main__':
    sys.exit(main())

# vi: sw=4:ts=4:expandtab
