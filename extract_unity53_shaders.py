#!/usr/bin/env python3

import sys, os, argparse, glob, struct
import extract_unity_shaders

class ParseError(Exception): pass

def align(file, alignment):
    off = file.tell()
    mod = off % alignment
    if mod == 0:
        return
    file.seek(alignment - mod, 1)

def add_header(headers, header):
    headers.append(header)
    print(header)

def decode_cb_definition(file, headers):
    (name_len,) = struct.unpack('<I', file.read(4))
    cb_name = file.read(name_len).decode('ascii')
    align(file, 4)
    (cb_size, num_entries) = struct.unpack('<2I', file.read(8))
    add_header(headers, 'ConstBuffer "{}" {}'.format(cb_name, cb_size))
    for j in range(num_entries):
        (name_len,) = struct.unpack('<I', file.read(4))
        entry_name = file.read(name_len).decode('ascii')
        align(file, 4)
        (zero, type_size1, type_size2, type3, one, offset) = struct.unpack('<6I', file.read(24))
        assert(zero == 0)
        assert(one == 1)
        if type_size1 == 1:
            assert(type3 == 0)
            if type_size2 == 1:
                add_header(headers, 'Float {} [{}]'.format(offset, entry_name))
            elif type_size2 == 4:
                add_header(headers, 'Vector {} [{}]'.format(offset, entry_name))
            elif type_size2 == 3:
                add_header(headers, 'Vector {} [{}] {}'.format(offset, entry_name, type_size2))
            else:
                raise ParseError('Unknown type_size2: {} for {}, type_size1: {}'.format(type_size2, entry_name, type_size1))
        elif type_size1 == 4:
            assert(type3 == 1)
            if type_size2 == 4:
                add_header(headers, 'Matrix {} [{}]'.format(offset, entry_name))
            elif type_size2 == 3:
                add_header(headers, 'Matrix {} [{}] {}'.format(offset, entry_name, type_size2))
            else:
                # matrix of size 2 might be valid as well
                assert(False)
        else:
            assert(False)

def decode_bind(file, headers):
    (name_len,) = struct.unpack('<I', file.read(4))
    bind_name = file.read(name_len).decode('ascii')
    align(file, 4)
    (bind_type, bind_slot, texture_type, sampler_slot, zero) = struct.unpack('<2I2BH', file.read(12))
    assert(zero == 0)
    if bind_type == 0:
        texture_type = {
                2: '2D',
                4: 'CUBE',
        }[texture_type]
        add_header(headers, 'SetTexture {} [{}] {} {}'.format(bind_slot, bind_name, texture_type, sampler_slot))
    elif bind_type == 1:
        assert(texture_type == 0)
        assert(sampler_slot == 0)
        add_header(headers, 'BindCB "{}" {}'.format(bind_name, bind_slot))
    else:
        assert(False)

def extract_shader_at(file, offset, size):
    saved_offset = file.tell()
    headers = []
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
            keyword = file.read(keyword_len).decode('ascii')
            print('    Keyword %i: "%s"' % (i, keyword))
            align(file, 4)

        (shader_size, u8a, u8b, u8c, u8d, u8e) = struct.unpack('<I5B', file.read(9))
        print('  shader size: {0} (0x{0:08x})'.format(shader_size))
        print('  u8: {:02x} {:02x} {:02x} {:02x} {:02x}'.format(u8a, u8b, u8c, u8d, u8e)) # Think this is related to the bindings

        shader = file.read(shader_size)
        align(file, 4)
        # TODO: DX9
        hash = '%016x' % extract_unity_shaders.fnv_3Dmigoto_shader(shader)
        dest = '%s--s' % hash
        print('Extracting %s.bin...' % dest)
        with open(dest + '.bin', 'wb') as out:
            out.write(shader)

        bind_info_size = size - (file.tell() - offset)
        print('  Remaining %i bytes' % bind_info_size)
        pos = file.tell()
        with open(dest + '.rem', 'wb') as out:
            out.write(file.read(bind_info_size))
        file.seek(pos)
        # print(file.read(bind_info_size))

        # Have not fully deciphered the data around this point, and depending
        # on the values the size can vary. For now use many asserts to catch
        # any deviations for analysis.
        (u10,) = struct.unpack('<I', file.read(4))
        print('  u10: {0}'.format(u10))
        if u10 == 0:
            (u11,) = struct.unpack('<I', file.read(4))
            print('  u11: {0}'.format(u11))
            if u11 == 0: # DX9 only?
                (u12, u13, u14, u15, u16, u17) = struct.unpack('<6I', file.read(24))
                print('  u12: {0}'.format(u12))
                print('  u13: {0}'.format(u13))
                print('  u14: {0}'.format(u14))
                print('  u15: {0}'.format(u15))
                print('  u16: {0}'.format(u16))
                print('  u17: {0}'.format(u17))
                assert(u12 in (1, 3))
                assert(u13 in (2, 3, 4))
                assert(u14 == 1)
                assert(u15 == 0)
                assert(u16 == 0)
                assert(u17 in (1, 5))
            else:
                num_sections = u11
                (u12, u13, u14) = struct.unpack('<3I', file.read(12))
                print('  num_sections: {0}'.format(num_sections))
                print('  u12: {0}'.format(u12))
                print('  u13: {0}'.format(u13))
                print('  u14: {0}'.format(u14))
                assert(u12 == 0)
                assert(u13 == 0)
                assert(u14 == 0)

                for i in range(num_sections-1):
                    decode_cb_definition(file, headers)

                (num_binds,) = struct.unpack('<I', file.read(4))
                for i in range(num_binds):
                    decode_bind(file, headers)

                assert(file.tell() - size - offset == 0)

        elif (u10 == 1): # DX9 only?
                (u11, u12, u13) = struct.unpack('<3I', file.read(12))
                print('  u11: {0}'.format(u11))
                print('  u12: {0}'.format(u12))
                print('  u13: {0}'.format(u13))
                assert(u11 == 0)
                assert(u12 == 0)
                assert(u13 in (0, 7, 8, 9, 10, 11, 15))
        elif (u10 == 2):
                (u11, u12, u13, u14, u15, u16, u17, u18) = struct.unpack('<8I', file.read(32))
                print('  u11: {0}'.format(u11))
                print('  u12: {0}'.format(u12))
                print('  u13: {0}'.format(u13))
                print('  u14: {0}'.format(u14))
                print('  u15: {0}'.format(u15))
                print('  u16: {0}'.format(u16))
                print('  u17: {0}'.format(u17))
                print('  u18: {0}'.format(u18))
                assert(u11 == 0)
                assert(u12 == 0)
                assert(u13 in (1, 3))
                assert(u14 in (2, 4))
                assert(u15 in (4, 2))
                assert(u16 == 0)
                assert(u17 == 0)
                assert(u18 == 0)
        else:
            assert(False)

        if headers:
            extract_unity_shaders.add_vanity_tag(headers)
            headers = extract_unity_shaders.commentify(headers)
            with open('%s_headers.txt' % dest, 'w') as f:
                f.write(headers)

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
