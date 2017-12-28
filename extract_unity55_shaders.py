#!/usr/bin/env python3

import sys, os, argparse, glob, struct, zlib, itertools
import extract_unity_shaders, extract_unity53_shaders
from extract_unity53_shaders import align

def parse_string(file):
    (length,) = struct.unpack('<I', file.read(4))
    string = file.read(length).decode('ascii')
    align(file, 4)
    return string

def parse_properties_table(file):
    (table_len,) = struct.unpack('<I', file.read(4))
    if table_len == 0:
        return

    print('Properties {')
    for i in range(table_len):
        name = parse_string(file)
        desc = parse_string(file)
        (u1, u2, u3, r, g, b, a) = struct.unpack('<3I4f', file.read(7*4))
        color = parse_string(file)
        (u4,) = struct.unpack('<I', file.read(4))
        # FIXME: Match the formatting of the old .shader files
        print('  {name} "{desc}" {u1:x} {u2:x} {u3:x} {r} {g} {b} {a} "{color}" {u4}'.format(
            name=name, desc=desc, u1=u1, u2=u2, u3=u3, r=r, g=g, b=b, a=a, color=color, u4=u4))
    print('}')

def parse_keywords_and_bindings_table(file):
    (num_keywords_and_bindings,) = struct.unpack('<I', file.read(4))
    keywords_and_bindings_dict = {}

    print('  Total keywords and bindings: %i' % num_keywords_and_bindings)
    for i in range(num_keywords_and_bindings):
        keyword_or_binding_name = parse_string(file)
        (keyword_idx,) = struct.unpack('<I', file.read(4))
        assert(keyword_idx not in keywords_and_bindings_dict)
        keywords_and_bindings_dict[keyword_idx] = keyword_or_binding_name
        print('    Keyword/binding[%i]: %s' % (keyword_idx, keyword_or_binding_name))

def check_init_indices(i, name):
    # For now going on the assumption that the order of this table is constant,
    # but not all entries are valid - if that is true, than we should see
    # consistent names in the same position.
    if name == '<noninit>': return
    if i == 77: assert(name == 'unity_FogStart')
    if i == 78: assert(name == 'unity_FogEnd')
    if i == 79: assert(name == 'unity_FogDensity')
    if i == 84: assert(name == 'unity_FogColor')

def print_unknown_init_entry(file, i, pos, type, val, name):
    print('    Init[{i} @ 0x{off:08x}]: {type}: {val} {name}'.format(
        i=i, off=pos, type=type, val=val, name=name))
    check_init_indices(i, name)

def parse_unknown_init_float_entry(file, i):
    pos = file.tell()
    (val,) = struct.unpack('<f', file.read(4))
    name = parse_string(file)
    print_unknown_init_entry(file, i, pos, 'float', '%.9g' % val, name)

def parse_unknown_init_float2_entry(file, i):
    pos = file.tell()
    vals = struct.unpack('<2f', file.read(8))
    name = parse_string(file)
    print_unknown_init_entry(file, i, pos, 'float2', '%.9g %.9g' % vals, name)

def parse_unknown_init_color_entry(file, i):
    pos = file.tell()
    name = parse_string(file)
    (val,) = struct.unpack('<I', file.read(4))
    print_unknown_init_entry(file, i, pos, 'color', '0x%08x' % val, name)

def parse_unknown_init_table(file):
    print('  Unknown Initialisation Table:')
    # No idea how to tell how large this table is, or which entries are what types
    # Maybe it is hardcoded in Unity? I sense an amateur coder at work here.
    for i in range(56):
        parse_unknown_init_float_entry(file, i)
    parse_unknown_init_float2_entry(file, 56)
    for i in range(57, 84):
        parse_unknown_init_float_entry(file, i)
    parse_unknown_init_color_entry(file, 84)

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

def parse_unknown_subshader_table(file):
    hack_end = file.tell() + 0x9c0 # FIXME: Remove this
    # At a guess, this might be the remaining info from the old .shader files,
    # such as the OpenGL shader GPU IDs
    print('  Subshader(?) table:')

    (unknown_offset, num_subshader_tags) = struct.unpack('<2I', file.read(8))
    ## This looks like an offset, since it gets progressively larger in each new
    ## metadata section. The offset is too large to refer to this file as is
    ## though - maybe post decompression?
    print('    Unknown offset: 0x{0:08x} {0}'.format(unknown_offset))
    print('    Num subshader(?) tags: %i' % num_subshader_tags)
    if num_subshader_tags:
        print('      Tags {', end='')
        for i in range(num_subshader_tags):
            print(' "%s"="%s"' % (parse_string(file), parse_string(file)), end='')
        print(' }')

    (u1, u2, u3, unknown_table_len) = struct.unpack('<4I', file.read(16))
    assert(u1 == 0)
    assert(u2 == 0)
    assert(u3 == 6)
    print('    Unknown table 1 len: %u' % unknown_table_len)

    for i in range(unknown_table_len):
        print('      Unknown table 1 entry %i' % i)
        data = file.read(136)
        hexdump(data, file.tell(), indent=6, width=24)

    (unknown_table_len,) = struct.unpack('<I', file.read(4))
    print('    Unknown table 2 len: %u' % unknown_table_len)

    for i in range(unknown_table_len):
        print('      Unknown table 2 entry %i' % i)
        data = file.read(64)
        hexdump(data, file.tell(), indent=6, width=24)

    u4 = struct.unpack('<8I', file.read(32))
    assert(u4 == (0,)*8)

    (num_pass_tags,) = struct.unpack('<I', file.read(4))
    if num_pass_tags:
        print('      Tags {', end='')
        for i in range(num_pass_tags):
            print(' "%s"="%s"' % (parse_string(file), parse_string(file)), end='')
        print(' }')

    (u5,) = struct.unpack('<I', file.read(4))
    assert(u5 == 0)

    shader_name = parse_string(file)
    print('Shader Name: %s' % shader_name)

    u6 = struct.unpack('<4I', file.read(16))
    assert(u6 == (0,)*4)

    data = file.read(100)
    hexdump(data, file.tell(), indent=4, width=24)

    # FIXME: Remove this
    hack_data = file.read(hack_end - file.tell())
    hexdump(hack_data, file.tell(), indent=2, width=24)

def parse_unity55_shader(filename):
    file = open(filename, 'rb')

    (asset_name_len,) = struct.unpack('<I', file.read(4))
    assert(asset_name_len == 0)

    parse_properties_table(file)

    # Maybe number of subshaders and/or passes?
    (u1, num_something) = struct.unpack('<2I', file.read(8))
    assert(u1 == 1)

    print('Number of shader metadata sections: %i' % num_something)
    for i in range(num_something):
        print(' Shader metadata section %i:' % i)
        parse_keywords_and_bindings_table(file)

        (u3, u4) = struct.unpack('<2I', file.read(8))
        assert(u3 == 0)
        assert(u4 == 0)

        parse_unknown_init_table(file)

        parse_unknown_subshader_table(file)

        # TODO: Parse the next data structure, whatever it is
        if num_something > 1:
            print(' WARNING FIXME: Skipping %i remaining shader metadata sections' % (num_something - i))
            break

    print('TODO: Extract actual shaders...')

def parse_args():
    global args
    parser = argparse.ArgumentParser(description = 'Unity 5.5 Shader Extractor')
    parser.add_argument('shaders', nargs='+',
            help='List of compiled Unity shader files to parse')
    # TODO parser.add_argument('--type', action='append', choices=('d3d9', 'd3d11'),
    # TODO         help='Filter types of shaders to process, useful to avoid unnecessary slow hash calculations')
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
        parse_unity55_shader(filename)
        print()

    # TODO write_delayed_shaders()

if __name__ == '__main__':
    sys.exit(main())

# vi: sw=4:ts=4:expandtab
