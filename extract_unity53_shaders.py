#!/usr/bin/env python3

import sys, os, argparse, glob, struct, zlib, itertools
import extract_unity_shaders

shader_type_mapping = {
     1: (None, "opengl", "version 120"),
     4: (None, "gles3",  "version 300 es"),
     5: (None, "gles",   "version 100"),
     6: (None, "glcore", "version 150"),

     9: ("vp", "d3d9", "vs_2_0"),
    10: ("vp", "d3d9", "vs_3_0"),
    11: ("fp", "d3d9", "ps_2_0"),
    12: ("fp", "d3d9", "ps_3_0"),

    13: ("vp", "d3d11_9x", "vs_4_0_level_9_1"),
    14: ("fp", "d3d11_9x", "ps_4_0_level_9_1"),

    15: ("vp", "d3d11", "vs_4_0"),
    16: ("vp", "d3d11", "vs_5_0"),
    17: ("fp", "d3d11", "ps_4_0"),
    18: ("fp", "d3d11", "ps_5_0"),

    20: ("gp", "d3d11", "gs_5_0"),
    21: ("hp", "d3d11", "hs_5_0"),
    22: ("dp", "d3d11", "ds_5_0"),
}

api_mapping = {
    "opengl": "opengl",
    "gles3": "opengl",
    "gles": "opengl",
    "glcore": "opengl",
    "d3d9": "d3d9",
    "d3d11_9x": "d3d11",
    "d3d11": "d3d11",
}

def get_program_name(shader_type):
    return shader_type_mapping[shader_type][0]
def get_shader_api(shader_type):
    api = shader_type_mapping[shader_type][1]
    return (api, api_mapping[api])
def get_shader_model(shader_type):
    return shader_type_mapping[shader_type][2]

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
    headers.append('  ' + header)
    # print(header)

def decode_consts(file, headers, shader_type):
    (num_entries,) = struct.unpack('<I', file.read(4))
    for j in range(num_entries):
        (name_len,) = struct.unpack('<I', file.read(4))
        entry_name = file.read(name_len).decode('ascii')
        align(file, 4)
        (type1, type_size1, type_size2, is_matrix, array_len, offset) = struct.unpack('<6I', file.read(24))

        # Unity < 5.4 this was always 1 and arrays were spelt out with all
        # individual elements. From 5.4 onwards it is 0 for no array, or >= 1
        # for an array - we append a number to the name to give the same
        # results as old versions, though this won't technically be correct for
        # Unity 5.4 with an array length of 1, but that's a minor issue.
        if array_len > 1:
            entry_names = [ '%s%i' % (entry_name, n) for n in range(array_len) ]
        else:
            entry_names = [ entry_name ]

        for entry_name in entry_names:
            if type1 == 0: # Float
                if is_matrix == 1: # Matrix
                    if type_size1 == 4:
                        if type_size2 == 4:
                            add_header(headers, 'Matrix {} [{}]'.format(offset, entry_name))
                        else:
                            assert(type_size2 > 0 and type_size2 < 4)
                            add_header(headers, 'Matrix {} [{}] {}'.format(offset, entry_name, type_size2))
                            assert(shader_type == ShaderType.dx11) # Need to check syntax for other way around
                    else:
                        assert(type_size2 == 4)
                        assert(type_size1 > 0 and type_size1 < 4)
                        add_header(headers, 'Matrix {} [{}] {}'.format(offset, entry_name, type_size1))
                        assert(shader_type == ShaderType.dx9) # Need to check syntax for other way around
                else: # Not matrix
                    assert(is_matrix == 0)
                    if type_size2 == 1:
                        add_header(headers, 'Float {} [{}]'.format(offset, entry_name))
                    elif type_size2 == 4:
                        add_header(headers, 'Vector {} [{}]'.format(offset, entry_name))
                    elif type_size2 in (2, 3):
                        add_header(headers, 'Vector {} [{}] {}'.format(offset, entry_name, type_size2))
                    else:
                        raise ParseError('Unknown type_size2: {} for {}, type_size1: {}'.format(type_size2, entry_name, type_size1))
            elif type1 == 1: # Int
                assert(type_size1 == 1)
                assert(is_matrix == 0)
                if type_size2 == 1:
                    add_header(headers, 'ScalarInt {} [{}]'.format(offset, entry_name))
                elif type_size2 in (2, 3, 4):
                    add_header(headers, 'VectorInt {} [{}] {}'.format(offset, entry_name, type_size2))
                else:
                    raise ParseError('Unknown type_size2: {} for {}, type_size1: {}'.format(type_size2, entry_name, type_size1))
            elif type1 == 2: # Bool
                assert(type_size1 == 1)
                assert(is_matrix == 0)
                if type_size2 == 1:
                    add_header(headers, 'ScalarBool {} [{}]'.format(offset, entry_name))
                elif type_size2 in (2, 3, 4):
                    add_header(headers, 'VectorBool {} [{}] {}'.format(offset, entry_name, type_size2))
                else:
                    raise ParseError('Unknown type_size2: {} for {}, type_size1: {}'.format(type_size2, entry_name, type_size1))
            else:
                raise ParseError('Unknown name: {} type1: {} type_size1: {} type_size2: {} type3: {} offset: {}'.format(entry_name, type1, type_size1, type_size2, type3, offset))
            offset += type_size1 * type_size2 * 4

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
        (bind_type, bind_slot, texture_type, sampler_slot, zero) = struct.unpack('<2i2bh', file.read(12))

        # Hmmm, could almost be a 3 byte integer, but that would be weird. Maybe just padding / stack garbage?
        assert((sampler_slot >= 0 and zero == 0) or (sampler_slot == -1 and zero == -1))

        if bind_type == 0:
            texture_type = {
                    2: '2D',
                    3: '3D',
                    4: 'CUBE',
            }[texture_type]
            add_header(headers, 'SetTexture {} [{}] {} {}'.format(bind_slot, bind_name, texture_type, sampler_slot))
        elif bind_type == 1:
            assert(texture_type == 0)
            assert(sampler_slot == 0)
            add_header(headers, 'BindCB "{}" {}'.format(bind_name, bind_slot))
        elif bind_type == 2:
            assert(texture_type == 0)
            assert(sampler_slot == 0)
            add_header(headers, 'SetBuffer {} [{}]'.format(bind_slot, bind_name))
        else:
            assert(False)

def decode_dx9_bind_info(file, headers):
    decode_consts(file, headers, ShaderType.dx9)
    decode_binds(file, headers)

def decode_dx11_bind_info(file, num_sections, headers):
    print('num dx11 bind info sections: {0}'.format(num_sections))
    decode_constbuffers(file, num_sections-1, headers, ShaderType.dx11)
    decode_binds(file, headers)

def dump_raw_bind_info(file, dest, section_offset, section_size):
    return # Remove to enable debugging dump

    bind_info_size = section_size - (file.tell() - section_offset)
    pos = file.tell()
    with open(dest + '.rem', 'wb') as out:
        out.write(file.read(bind_info_size))
    file.seek(pos)

def finalise_headers(headers, sub_program):
    extract_unity_shaders.add_header_hash(headers, sub_program)
    extract_unity_shaders.add_vanity_tag(headers)
    return extract_unity_shaders.commentify(headers)

def delay_writing_shader(shader_cache, hash, dest, bin, headers, sub_program):
    if hash not in shader_cache:
        cache = [set(), [], [], bin]
        shader_cache[hash] = cache
    else:
        cache = shader_cache[hash]
        assert(cache[3] == bin)
    cache[0].add(dest)
    cache[1].append(headers)
    cache[2].append(sub_program)

dx9_shader_cache = {}
dx11_shader_cache = {}

def delay_writing_dx9_shader(hash, dest, bin, headers, sub_program):
    return delay_writing_shader(dx9_shader_cache, hash, dest, bin, headers, sub_program)

def delay_writing_dx11_shader(hash, dest, bin, headers, sub_program):
    return delay_writing_shader(dx11_shader_cache, hash, dest, bin, headers, sub_program)

def _write_delayed_shaders(shader_cache, export):
    for (hash, shaders) in sorted(shader_cache.items()):
        (dests, uncombined_headers, sub_programs, bin) = shaders
        if len(sub_programs) > 1:
            (shaders, headers) = extract_unity_shaders.shader_variant_summary_header(sub_programs)
            # Unlike the old script, we combine all the header variants
            # together - this should usually make it clearer and will work with
            # the separate 5.3 header section. There were some cases where this
            # would create too much diff garbage in the old script which I'll
            # need to keep an eye out for, but hopefully the simpler header
            # format will reduce the likelihood of that...
            while any(uncombined_headers):
                extract_unity_shaders._combine_similar_headers(headers, uncombined_headers)
        else:
            headers = uncombined_headers[0]
        headers = finalise_headers(headers, sub_programs[0])
        output_files = export(dests.pop(), bin, headers)
        for dest in dests:
            for (filename, contents) in output_files.items():
                mode = 'w'
                if isinstance(contents, bytes):
                    mode = 'wb'
                copy_dest = os.path.join(os.path.dirname(dest), os.path.basename(filename))
                print('  |--> %s' % copy_dest)
                with open (copy_dest, mode) as out:
                    out.write(contents)

def write_delayed_shaders():
    _write_delayed_shaders(dx9_shader_cache, extract_unity_shaders.export_dx9_shader_binary)
    _write_delayed_shaders(dx11_shader_cache, extract_unity_shaders.export_dx11_shader)

processed = set()

def extract_opengl_shader(file, shader_size, headers, shader):
    shader.sub_program.shader_asm = file.read(shader_size).decode('utf-8')
    try:
        hash = {}
        for program_name in ('fp', 'vp'):
            shader.program.name = program_name;
            hash[program_name] = extract_unity_shaders.hash_gl_crc(shader.sub_program)
            add_header(headers, ('{} hash: {:x}'.format(program_name, hash[program_name])))
        for program_name in ('fp', 'vp'):

            # FIXME: Write out any with duplicate hashes in case we ever have
            # an autofix that needs to e.g. find all PS corresponding with a
            # given VS hash, where that hash appears in multiple distinct
            # shaders (e.g. Internal-PrePassLighting and
            # Internal-DeferredReflection share the same VS, but have differing PS)

            if hash[program_name] in processed:
                continue
            processed.add(hash[program_name])

            shader.program.name = program_name;
            extract_unity_shaders._add_shader_hash_gl_crc(shader.sub_program, hash[program_name])
            path_components = extract_unity_shaders.export_filename_combined_short(shader)
            dest = extract_unity_shaders.path_components_to_dest(path_components)

            print('Extracting %s.glsl...' % dest)
            with open('%s.glsl' % dest, 'w') as out:
                out.write(extract_unity_shaders.fixup_glsl_like_unity(shader.sub_program))
            with open('%s.info' % dest, 'w') as f:
                f.write('\n'.join(headers))
    except extract_unity_shaders.BogusShader:
        return

def extract_directx9_shader(file, shader_size, headers, section_offset, section_size, shader):
    bin = file.read(shader_size)
    align(file, 4) # Seems ok without this - looks like the shader binary is always a multiple of 4 bytes
    assert(bin[8:12] == b'CTAB') # XXX: May fail for shaders without embedded constant tables

    hash = zlib.crc32(bin)

    extract_unity_shaders._add_shader_hash_asm_crc(shader.sub_program, zlib.crc32(bin))
    path_components = extract_unity_shaders.export_filename_combined_short(shader)
    dest = extract_unity_shaders.path_components_to_dest(path_components)

    dump_raw_bind_info(file, dest, section_offset, section_size)

    # Have not fully deciphered the data around this point, and depending
    # on the values the size can vary. Making a best guess based on
    # obsevations that DX9 ends in 0, 0. Values seem to be in pairs. Suspect
    # they are related to the generic "Bind" statements in previous Unity
    # versions, but can't make heads or tails of them.
    undeciphered3 = list(struct.unpack('<I', file.read(4)))
    undeciphered3.extend(consume_until_double_zero(file))
    add_header(headers, ('undeciphered3:' + ' {}'*len(undeciphered3)).format(*undeciphered3))

    decode_dx9_bind_info(file, headers)
    assert(file.tell() - section_size - section_offset == 0)

    delay_writing_dx9_shader(hash, dest, bin, headers, shader.sub_program)

def extract_directx11_shader(file, shader_size, headers, section_offset, section_size, shader, date):
    # Is this the correct way to detect this? Could be a file version, but it
    # looks suspiciously like a date (but 2015? Last year for an update
    # released this year?), so I'm not certain this is correct. If not this,
    # maybe just check the Unity version for 5.4?
    if date == 201509030:
        u8len = 5
    elif date in (201510240, 201608170): # Seen in Firewatch Unity 5.4 update / 2016 date in Unity 5.5
        u8len = 6
    else:
        assert(False)
    u8 = struct.unpack('<%ib' % u8len, file.read(u8len))
    add_header(headers, 'undeciphered2: {}'.format(' '.join(map(str, u8)))) # Think this is related to the bindings

    bin = file.read(shader_size - u8len)
    align(file, 4)
    assert(bin[:4] == b'DXBC')

    hash = extract_unity_shaders.fnv_3Dmigoto_shader(bin)

    extract_unity_shaders._add_shader_hash_fnv(shader.sub_program, hash)
    path_components = extract_unity_shaders.export_filename_combined_short(shader)
    dest = extract_unity_shaders.path_components_to_dest(path_components)

    # print('Extracting %s.bin...' % dest)
    # with open('%s.bin' % dest, 'wb') as out:
    #     out.write(bin)

    dump_raw_bind_info(file, dest, section_offset, section_size)

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
    add_header(headers, ('undeciphered3:' + ' {}'*len(undeciphered3)).format(*undeciphered3))

    decode_dx11_bind_info(file, num_sections, headers)
    assert(file.tell() - section_size - section_offset == 0)

    delay_writing_dx11_shader(hash, dest, bin, headers, shader.sub_program)

def synthesize_sub_program(name):
    class Shader(object):
        keyword = 'Shader'
        def __init__(self, name):
            self.name = name
    class SubShader(object):
        keyword = 'SubShader'
        def __init__(self, name):
            self.parent = Shader(name)
    class Pass(object):
        keyword = 'Pass'
        def __init__(self, name):
            self.parent = SubShader(name)
    class Program(object):
        keyword = 'Program'
        def __init__(self, name):
            self.parent = Pass(name)
    class SubProgram(object):
        keyword = 'SubProgram'
        def __init__(self, name):
            self.parent = Program(name)
    return SubProgram(name)

# NOTE: Also called from extract_unity55_shaders.py
def extract_shader_at(file, offset, size, filename, sub_programs, skip_classic_headers=False):
    saved_offset = file.tell()
    file.seek(offset)
    try:
        (date, shader_type, u3, u4, u5) = struct.unpack('<5i', file.read(20))
        assert(date in (201509030, 201510240, 201608170)) # New date/version(?) seen in Firewatch Unity 5.4 update
        u6 = None
        if date == 201608170: # Unity 5.5
            (u6,) = struct.unpack('<i', file.read(4))
        (num_keywords,) = struct.unpack('<i', file.read(4))
        api, conceptual_api = get_shader_api(shader_type)

        if args.type and conceptual_api not in args.type:
                file.seek(saved_offset)
                return

        headers = []
        if skip_classic_headers:
            sub_program = synthesize_sub_program(os.path.splitext(os.path.splitext(filename)[0])[0])
        elif callable(sub_programs):
            sub_program = sub_programs(shader_type)
            headers = extract_unity_shaders.collect_headers(sub_program)
            headers.append('')
        else:
            sub_program = sub_programs[0]
            headers.extend(extract_unity_shaders.combine_similar_headers(sub_programs) + [''])
        headers.append('Unity 5.3 headers extracted from %s:' % filename)
        shader = extract_unity_shaders.get_parents(sub_program)

        program_name = get_program_name(shader_type)
        add_header(headers, 'API {}'.format(api))
        add_header(headers, 'Shader model {}'.format(get_shader_model(shader_type)))
        add_header(headers, 'undeciphered1: {} {} {} {}'.format(date, u3, u4, u5))
        if u6 is not None:
            add_header(headers, 'undeciphered1a: {}'.format(u6))
        if skip_classic_headers:
            shader.program.name = program_name
            shader.sub_program.name = api
        else:
            assert(shader.program.name == program_name or program_name is None)
            assert(shader.sub_program.name.split(' ')[0] == api) # sub_program "d3d9 hw_tier01" seen in Firewatch Unity 5.4 update

        keywords = []
        for i in range(num_keywords):
            (keyword_len,) = struct.unpack('<I', file.read(4))
            keywords.append(file.read(keyword_len).decode('ascii'))
            align(file, 4)
        if keywords:
            add_header(headers, 'Keywords { "%s" }' % '" "'.join(keywords))

        (shader_size,) = struct.unpack('<i', file.read(4))

        if extract_unity_shaders.is_opengl_shader(sub_program):
            extract_opengl_shader(file, shader_size, headers, shader)
        elif api == 'd3d9':
            extract_directx9_shader(file, shader_size, headers, offset, size, shader)
        elif api in ('d3d11', 'd3d11_9x'):
            extract_directx11_shader(file, shader_size, headers, offset, size, shader, date)
        elif api in ('gles', 'gles3'):
            # See explanation in is_opengl_shader
            pass
        else:
            raise ParseError('Unknown shader type %i' % shader_type)

        print()
        file.seek(saved_offset)
    except:
        file.seek(saved_offset)
        raise

def parse_unity53_shader(filename):
    file = open(filename, 'rb')

    if args.skip_classic_headers:
        sub_program_generator = itertools.repeat(None)
    else:
        shader_tree = extract_unity_shaders.parse_tree(os.path.splitext(filename)[0])
        sub_program_generator = extract_unity_shaders.walk_sub_programs(shader_tree)

    (num_shaders,) = struct.unpack('<I', file.read(4))
    print('Num shaders: %i' % num_shaders)
    for i in range(num_shaders):
        sub_programs = next(sub_program_generator)
        (offset, size) = struct.unpack('<II', file.read(8))
        print('Shader %i offset: %i, size: %i' % (i, offset, size))
        extract_shader_at(file, offset, size, os.path.basename(filename), sub_programs, args.skip_classic_headers)

def parse_args():
    global args
    parser = argparse.ArgumentParser(description = 'Unity 5.3 Shader Extractor')
    parser.add_argument('shaders', nargs='+',
            help='List of compiled Unity shader files to parse')
    parser.add_argument('--skip-classic-headers', action='store_true',
            help='Skip extracting the classic Unity headers from a corresponding .shader file (not recommended)')
    parser.add_argument('--type', action='append', choices=('d3d9', 'd3d11'),
            help='Filter types of shaders to process, useful to avoid unnecessary slow hash calculations')
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

    write_delayed_shaders()

if __name__ == '__main__':
    sys.exit(main())

# vi: sw=4:ts=4:expandtab
