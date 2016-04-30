#!/usr/bin/env python3

import sys, os, argparse, glob, struct, zlib
import extract_unity_shaders

shader_type_mapping = {
     1: (None, "OpenGL version 120"),
     4: (None, "OpenGL version 300 es"),
     5: (None, "OpenGL version 100"),
     6: (None, "OpenGL version 150"),

     9: ("vp", "DirectX9 vs_2_0"),
    10: ("vp", "DirectX9 vs_3_0"),
    11: ("fp", "DirectX9 ps_2_0"),
    12: ("fp", "DirectX9 ps_3_0"),

    13: ("vp", "DirectX11 (Feature Level 9) vs_4_0 + vs_2_0"),
    14: ("fp", "DirectX11 (Feature Level 9) ps_4_0 + ps_2_0"),

    15: ("vp", "DirectX11 vs_4_0"),
    16: ("vp", "DirectX11 vs_5_0"),
    17: ("fp", "DirectX11 ps_4_0"),
    18: ("fp", "DirectX11 ps_5_0"),
}

def get_shader_type_name(shader_type):
    return shader_type_mapping[shader_type][1]

def get_program_name(shader_type):
    return shader_type_mapping[shader_type][0]

class ParseError(Exception): pass

class ShaderType(object):
    dx9 = 1
    dx11 = 2
    opengl = 3

def align(file, alignment):
    off = file.tell()
    mod = off % alignment
    if mod == 0:
        return
    file.seek(alignment - mod, 1)

def consume_until_double_zero(file):
    ret = []
    while True:
        tmp = struct.unpack('<2I', file.read(8))
        if tmp == (0, 0):
            return ret
        ret.extend(tmp)

def consume_until_dx11_num_sections(file, undeciphered3):
    data = consume_until_double_zero(file)
    undeciphered3.extend(data[:-2])
    num_sections = data[-2]
    assert(data[-1] == 0)
    return num_sections

def add_header(headers, header):
    headers.append(header)
    print(header)

def decode_consts(file, headers, shader_type):
    (num_entries,) = struct.unpack('<I', file.read(4))
    for j in range(num_entries):
        (name_len,) = struct.unpack('<I', file.read(4))
        entry_name = file.read(name_len).decode('ascii')
        align(file, 4)
        (type1, type_size1, type_size2, type3, one, offset) = struct.unpack('<6I', file.read(24))
        assert(one == 1)
        if type1 == 0: # Float
            if type_size1 == 1:
                assert(type3 == 0)
                if type_size2 == 1:
                    add_header(headers, 'Float {} [{}]'.format(offset, entry_name))
                elif type_size2 == 4:
                    add_header(headers, 'Vector {} [{}]'.format(offset, entry_name))
                elif type_size2 in (2, 3):
                    add_header(headers, 'Vector {} [{}] {}'.format(offset, entry_name, type_size2))
                else:
                    raise ParseError('Unknown type_size2: {} for {}, type_size1: {}'.format(type_size2, entry_name, type_size1))
            elif type_size1 == 4:
                assert(type3 == 1)
                if type_size2 == 4:
                    add_header(headers, 'Matrix {} [{}]'.format(offset, entry_name))
                elif type_size2 in (2, 3): # 2x4 unconfirmed for DX11
                    add_header(headers, 'Matrix {} [{}] {}'.format(offset, entry_name, type_size2))
                    assert(shader_type == ShaderType.dx11) # Need to check syntax for other way around
                else:
                    assert(False)
            elif type_size1 in (2, 3):
                assert(type_size2 == 4)
                assert(type3 == 1)
                add_header(headers, 'Matrix {} [{}] {}'.format(offset, entry_name, type_size1))
                assert(shader_type == ShaderType.dx9) # Need to check syntax for other way around
            else:
                raise ParseError('Unknown name: {} type_size1: {} type_size2: {} type3: {} offset: {}'.format(entry_name, type_size1, type_size2, type3, offset))
        elif type1 == 1: # Int
            assert(type_size1 == 1)
            assert(type_size2 == 4)
            assert(type3 == 0)
            add_header(headers, 'VectorInt {} [{}] {}'.format(offset, entry_name, type_size2))
        elif type1 == 2: # Bool
            assert(type_size1 == 1)
            assert(type_size2 == 1)
            assert(type3 == 0)
            add_header(headers, 'ScalarBool {} [{}]'.format(offset, entry_name))
        else:
            raise ParseError('Unknown name: {} type1: {} type_size1: {} type_size2: {} type3: {} offset: {}'.format(entry_name, type1, type_size1, type_size2, type3, offset))

def decode_constbuffers(file, num_cbs, headers, shader_type):
    for i in range(num_cbs):
        (name_len,) = struct.unpack('<I', file.read(4))
        cb_name = file.read(name_len).decode('ascii')
        align(file, 4)
        (cb_size,) = struct.unpack('<I', file.read(4))
        add_header(headers, 'ConstBuffer "{}" {}'.format(cb_name, cb_size))
        decode_consts(file, headers, shader_type)

def decode_binds(file, headers):
    (num_binds,) = struct.unpack('<I', file.read(4))
    for i in range(num_binds):
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

def decode_dx9_bind_info(file, headers):
    decode_consts(file, headers, ShaderType.dx9)
    decode_binds(file, headers)

def decode_dx11_bind_info(file, num_sections, headers):
    print('num dx11 sections: {0}'.format(num_sections))
    decode_constbuffers(file, num_sections-1, headers, ShaderType.dx11)
    decode_binds(file, headers)

def save_external_headers(dest, headers):
    extract_unity_shaders.add_vanity_tag(headers)
    headers = extract_unity_shaders.commentify(headers)
    with open('%s_headers.txt' % dest, 'w') as f:
        f.write(headers)


def extract_opengl_shader(file, shader_size, headers, shader_name):
    shader = file.read(shader_size)
    try:
        hash = {}
        shader_txt = shader.decode('utf-8')
        for program_name in ('fp', 'vp'):
            hash[program_name] = extract_unity_shaders.hash_gl_crc(shader_txt, program_name)
            add_header(headers, ('{} hash: {:x}'.format(program_name, hash[program_name])))
        for program_name in ('fp', 'vp'):
            path_components = extract_unity_shaders._export_filename_combined_short(
                    hash[program_name], 'gl_crc32', '%x', shader_name, program_name)
            dest = extract_unity_shaders.path_components_to_dest(path_components)

            print('Extracting %s.glsl...' % dest)
            with open('%s.glsl' % dest, 'w') as out:
                out.write(extract_unity_shaders._fixup_glsl_like_unity(shader_txt, program_name))
            with open('%s.info' % dest, 'w') as f:
                f.write('\n'.join(headers))
    except extract_unity_shaders.BogusShader:
        return

def extract_directx9_shader(file, shader_size, headers, section_offset, section_size, shader_name, program_name):
    shader = file.read(shader_size)
    align(file, 4) # Seems ok without this - looks like the shader binary is always a multiple of 4 bytes
    assert(shader[8:12] == b'CTAB') # XXX: May fail for shaders without embedded constant tables

    hash = zlib.crc32(shader)
    path_components = extract_unity_shaders._export_filename_combined_short(
            hash, 'asm_crc32', '%08X', shader_name, program_name)
    dest = extract_unity_shaders.path_components_to_dest(path_components)

    print('Extracting %s.bin...' % dest)
    with open('%s.bin' % dest, 'wb') as out:
        out.write(shader)

    if True: # Useful for debugging
        bind_info_size = section_size - (file.tell() - section_offset)
        pos = file.tell()
        with open(dest + '.rem', 'wb') as out:
            out.write(file.read(bind_info_size))
        file.seek(pos)

    # Have not fully deciphered the data around this point, and depending
    # on the values the size can vary. Making a best guess based on
    # obsevations that DX9 ends in 0, 0. Values seem to be in pairs. Suspect
    # they are related to the generic "Bind" statements in previous Unity
    # versions, but can't make heads or tails of them.
    undeciphered3 = list(struct.unpack('<I', file.read(4)))
    undeciphered3.extend(consume_until_double_zero(file))
    add_header(headers, ('undeciphered3 (DX 9):' + ' {:x}'*len(undeciphered3)).format(*undeciphered3))

    decode_dx9_bind_info(file, headers)
    assert(file.tell() - section_size - section_offset == 0)

    save_external_headers(dest, headers)

def extract_directx11_shader(file, shader_size, headers, section_offset, section_size, shader_name, program_name):
    (u8a, u8b, u8c, u8d, u8e) = struct.unpack('<5b', file.read(5))
    add_header(headers, 'undeciphered2: {} {} {} {} {}'.format(u8a, u8b, u8c, u8d, u8e)) # Think this is related to the bindings

    shader = file.read(shader_size - 5)
    align(file, 4)
    assert(shader[:4] == b'DXBC')
    assert(u8c >= 0)
    assert(u8d >= 0)
    assert(u8e >= 0)

    hash = extract_unity_shaders.fnv_3Dmigoto_shader(shader)
    path_components = extract_unity_shaders._export_filename_combined_short(
            hash, '3Dmigoto', '%016x', shader_name, program_name)
    dest = extract_unity_shaders.path_components_to_dest(path_components)

    print('Extracting %s.bin...' % dest)
    with open('%s.bin' % dest, 'wb') as out:
        out.write(shader)

    if True: # Useful for debugging
        bind_info_size = section_size - (file.tell() - section_offset)
        pos = file.tell()
        with open(dest + '.rem', 'wb') as out:
            out.write(file.read(bind_info_size))
        file.seek(pos)

    # Have not fully deciphered the data around this point, and depending
    # on the values the size can vary. Making a best guess based on
    # obsevations that DX11 ends in num_sections, 0, 0, 0. If first value != 0
    # it is followed by two 0s. Values seem to be in pairs. Suspect they are
    # related to the generic "Bind" statements in previous Unity versions, but
    # can't make heads or tails of them.
    undeciphered3 = list(struct.unpack('<2I', file.read(8)))
    if undeciphered3[1]:
        undeciphered3.extend(struct.unpack('<2I', file.read(8)))

    num_sections = consume_until_dx11_num_sections(file, undeciphered3)
    add_header(headers, ('undeciphered3 (DX11):' + ' {:x}'*len(undeciphered3)).format(*undeciphered3))

    decode_dx11_bind_info(file, num_sections, headers)
    assert(file.tell() - section_size - section_offset == 0)

    save_external_headers(dest, headers)

def extract_shader_at(file, offset, size, shader_name):
    saved_offset = file.tell()
    headers = []
    file.seek(offset)
    try:
        (u1, shader_type, u3, u4, u5, num_keywords) = struct.unpack('<6i', file.read(24))
        assert(u1 == 0x0c02c8a6)
        add_header(headers, 'shader_type: {}'.format(get_shader_type_name(shader_type)))
        add_header(headers, 'undeciphered1: {} {} {}'.format(u3, u4, u5))

        keywords = []
        for i in range(num_keywords):
            (keyword_len,) = struct.unpack('<I', file.read(4))
            keywords.append(file.read(keyword_len).decode('ascii'))
            align(file, 4)
        if keywords:
            add_header(headers, 'Keywords { "%s" }' % '" "'.join(keywords))

        (shader_size,) = struct.unpack('<i', file.read(4))

        if shader_type in (1, 4, 5, 6):
            extract_opengl_shader(file, shader_size, headers, shader_name)
        elif shader_type in (9, 10, 11, 12):
            extract_directx9_shader(file, shader_size, headers, offset, size, shader_name, get_program_name(shader_type))
        elif shader_type in (13, 14, 15, 16, 17, 18):
            extract_directx11_shader(file, shader_size, headers, offset, size, shader_name, get_program_name(shader_type))
        else:
            raise ParseError('Unknown shader type %i' % shader_type)

        print()
        file.seek(saved_offset)
    except:
        file.seek(saved_offset)
        raise

def parse_unity53_shader(filename):
    file = open(filename, 'rb')

    # FIXME: Use name from .shader file for consistency with extract_unity_shaders:
    shader_name = os.path.splitext(os.path.splitext(os.path.basename(filename))[0])[0]

    (num_shaders,) = struct.unpack('<I', file.read(4))
    print('Num shaders: %i' % num_shaders)
    for i in range(num_shaders):
        (offset, size) = struct.unpack('<II', file.read(8))
        print('Shader %i offset: %i, size: %i' % (i, offset, size))
        extract_shader_at(file, offset, size, shader_name)

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
        parse_unity53_shader(filename)
        print()

if __name__ == '__main__':
    sys.exit(main())

# vi: sw=4:ts=4:expandtab
