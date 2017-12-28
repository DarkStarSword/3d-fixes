#!/usr/bin/env python3

import sys, os, argparse, glob, struct, zlib, itertools
import extract_unity_shaders, extract_unity53_shaders
from extract_unity53_shaders import align

def align_verify_zero(file, alignment):
    off = file.tell()
    mod = off % alignment
    if mod == 0:
        return
    data = file.read(mod)
    print(data)
    assert(data == b'\0' * mod)

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
        (attributes, type, flags, def0, def1, def2, def3) = struct.unpack('<3I4f', file.read(7*4))
        assert(attributes == 0) # FIXME: Attributes is probably an array, may be special cased for >= 0x10?
        def_texture = parse_string(file)
        (texdim,) = struct.unpack('<I', file.read(4))
        # FIXME: Match the formatting of the old .shader files
        print('  {name} "{desc}" {attributes:x} {type:x} {flags:x} {def0} {def1} {def2} {def3} "{def_texture}" {texdim}'.format(
            name=name, desc=desc, attributes=attributes, type=type, flags=flags, def0=def0,
            def1=def1, def2=def2, def3=def3, def_texture=def_texture, texdim=texdim))
    print('}')

def parse_name_indices_table(file):
    (num_keywords_and_bindings,) = struct.unpack('<I', file.read(4))
    keywords_and_bindings_dict = {}

    for i in range(num_keywords_and_bindings):
        name = parse_string(file)
        (idx,) = struct.unpack('<I', file.read(4))
        assert(idx not in keywords_and_bindings_dict)
        keywords_and_bindings_dict[idx] = name
        print('    Name[%i]: %s' % (idx, name))

def print_state_entry(name1, val, name2, indent=4):
    print('{indent}{name1:20}: {val} {name2}'.format(name1=name1, val=val, name2=name2, indent = ' ' * indent))
    #if name2 != '<noninit>':
    #    assert(name1 == name2)

def print_field(name, val, indent=4):
    print('{indent}{name:20}: {val}'.format(name=name, val=val, indent = ' ' * indent))

def parse_state_x4(file, verify_name, indent=4):
    (val,) = struct.unpack('<I', file.read(4))
    name = parse_string(file)
    print_state_entry(verify_name, '0x%08x' % val, name, indent=indent)

def parse_state_float(file, verify_name, indent=4):
    (val,) = struct.unpack('<f', file.read(4))
    name = parse_string(file)
    print_state_entry(verify_name, '%.9g' % val, name, indent=indent)

def parse_rt_blend_state(file, rt):
    print('   RT Blend State[%i]:' % rt)
    parse_state_float(file, 'srcBlend', indent=4)
    parse_state_float(file, 'destBlend', indent=4)
    parse_state_float(file, 'srcBlendAlpha', indent=4)
    parse_state_float(file, 'destBlendAlpha', indent=4)
    parse_state_float(file, 'blendOp', indent=4)
    parse_state_float(file, 'blendOpAlpha', indent=4)
    parse_state_float(file, 'colMask', indent=4)

def parse_stencil_op_state(file, op):
    print('   %s:' % op)
    parse_state_float(file, 'pass', indent=4)
    parse_state_float(file, 'fail', indent=4)
    parse_state_float(file, 'zFail', indent=4)
    parse_state_float(file, 'comp', indent=4)

def parse_state_color(file, name1):
    print('   %s:' % name1)
    parse_state_float(file, 'x', indent=4)
    parse_state_float(file, 'y', indent=4)
    parse_state_float(file, 'z', indent=4)
    parse_state_float(file, 'w', indent=4)
    name2 = parse_string(file)
    print('%s%s' % (' ' * 24, name2))

def parse_x4(file, name, indent=4):
    (val,) = struct.unpack('<I', file.read(4))
    print_field(name, '0x%08x' % val, indent=indent)

def parse_tags(file):
    (num_pass_tags,) = struct.unpack('<I', file.read(4))
    if num_pass_tags:
        print('   Tags {', end='')
        for i in range(num_pass_tags):
            print(' "%s"="%s"' % (parse_string(file), parse_string(file)), end='')
        print(' }')

def parse_state(file):
    (name_len,) = struct.unpack('<I', file.read(4))
    assert(name_len == 0) # Guess this is a string, but make sure first

    for rt in range(8):
        parse_rt_blend_state(file, rt)

    (rtSeparateBlend,) = struct.unpack('B', file.read(1))
    print('   RT Separate Blend: %i' % rtSeparateBlend)
    assert(file.read(3) == b'\0' * 3)

    parse_state_float(file, 'zTest', indent=3)
    parse_state_float(file, 'zWrite', indent=3)
    parse_state_float(file, 'culling', indent=3)
    parse_state_float(file, 'offsetFactor', indent=3)
    parse_state_float(file, 'offsetUnits', indent=3)
    parse_state_float(file, 'alphaToMask', indent=3)

    parse_stencil_op_state(file, 'stencilOp')
    parse_stencil_op_state(file, 'stencilOpFront')
    parse_stencil_op_state(file, 'stencilOpBack')

    parse_state_float(file, 'stencilSteadMask', indent=3)
    parse_state_float(file, 'stencilWriteMask', indent=3)
    parse_state_float(file, 'stencilRef', indent=3)
    parse_state_float(file, 'fogStart', indent=3)
    parse_state_float(file, 'fogEnd', indent=3)
    parse_state_float(file, 'fogDensity', indent=3)

    parse_state_color(file, 'fogColor')

    parse_x4(file, 'fogMode', indent=3)
    parse_x4(file, 'gpuProgramID', indent=3)

    parse_tags(file)

    parse_x4(file, 'LOD', indent=3)
    parse_x4(file, 'lighting', indent=3)

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

def parse_pass(file):
    parse_name_indices_table(file)

    (type,) = struct.unpack('<I', file.read(4))
    assert(type == 0)

    parse_state(file)

    parse_x4(file, 'ProgramMask', indent=3)

    # TODO: subprograms
    # TODO:   progVertex
    # TODO:   progFragment
    # TODO:   progGeometry
    # TODO:   progHull
    # TODO:   progDomain
    # TODO: hasInstancingVariant (1 byte)
    # TODO: UseName = parse_string(file)
    # TODO: Name = parse_string(file)
    # TODO: TextureName = parse_string(file)
    # TODO: parse_tags(file)

def parse_unity55_shader(filename):
    file = open(filename, 'rb')

    (asset_name_len,) = struct.unpack('<I', file.read(4))
    assert(asset_name_len == 0)

    parse_properties_table(file)

    (num_subshaders,) = struct.unpack('<I', file.read(4))
    print('Number of subshaders: %i' % num_subshaders)
    for subshader in range(num_subshaders):
        print(' Subshader %i:' % subshader)
        (num_passes,) = struct.unpack('<I', file.read(4))
        print('  Number of passes: %i' % num_passes)
        for pass_no in range(num_passes):
            print('  Pass %i:' % pass_no)
            parse_pass(file)
            if num_passes > 1:
                print(' WARNING FIXME: Skipping %i remaining passes' % (num_passes - pass_no))
                break
        if num_subshaders > 1:
            print(' WARNING FIXME: Skipping %i remaining subshaders' % (num_subshaders - subshader))
            break

    # TODO: Name = parse_string(file)
    # TODO: CustomEditorName = parse_string(file)
    # TODO: FallbackName = parse_string(file)
    # TODO: Dependencies
    # TODO: DisableNoSubshadersMessage

    # TODO: platforms
    # TODO: offsets
    # TODO: compressedLengths
    # TODO: decompressedLengths
    # TODO: compressedBlob

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
