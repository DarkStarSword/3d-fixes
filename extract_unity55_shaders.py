#!/usr/bin/env python3

import sys, os, argparse, glob, struct, zlib, itertools
import extract_unity_shaders, extract_unity53_shaders

def align(file, alignment):
    off = file.tell()
    mod = off % alignment
    if mod == 0:
        return
    data = file.read(alignment - mod)
    assert(data == b'\0' * (alignment - mod))

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
        (num_attributes,) = struct.unpack('<I', file.read(4))
        attributes = []
        for i in range(num_attributes):
            attributes.append(parse_string(file))
        (type, flags, def0, def1, def2, def3) = struct.unpack('<2I4f', file.read(6*4))
        def_texture = parse_string(file)
        (texdim,) = struct.unpack('<I', file.read(4))
        # FIXME: Match the formatting of the old .shader files
        print('  {name} "{desc}" {num_attributes:x} {type:x} {flags:x} {def0} {def1} {def2} {def3} "{def_texture}" {texdim}'.format(
            name=name, desc=desc, num_attributes=num_attributes, type=type, flags=flags, def0=def0,
            def1=def1, def2=def2, def3=def3, def_texture=def_texture, texdim=texdim))
        if attributes:
            print('    Attributes: ' + ', '.join(attributes))
    print('}')

def parse_name_indices_table(file):
    (num_names,) = struct.unpack('<I', file.read(4))
    name_dict = {}

    for i in range(num_names):
        name = parse_string(file)
        (idx,) = struct.unpack('<I', file.read(4))
        assert(idx not in name_dict)
        name_dict[idx] = name
        print('    Name[%i]: %s' % (idx, name))

    return name_dict

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
    return val

def parse_u4(file, name=None, indent=4):
    (val,) = struct.unpack('<I', file.read(4))
    if name is not None:
        print_field(name, '%i' % val, indent=indent)
    return val

def parse_byte(file, name=None, indent=4):
    (val,) = struct.unpack('B', file.read(1))
    if name is not None:
        print_field(name, '%i' % val, indent=indent)
    return val

def parse_tags(file, indent=3):
    (num_pass_tags,) = struct.unpack('<I', file.read(4))
    if num_pass_tags:
        print('%sTags {' % (' ' * indent), end='')
        for i in range(num_pass_tags):
            print(' "%s"="%s"' % (parse_string(file), parse_string(file)), end='')
        print(' }')

def parse_state(file):
    print('   State Name: %s' % parse_string(file))

    for rt in range(8):
        parse_rt_blend_state(file, rt)

    (rtSeparateBlend,) = struct.unpack('B', file.read(1))
    print('   RT Separate Blend: %i' % rtSeparateBlend)
    align(file, 4)

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

def parse_channels(file):
    (num_bindings,) = struct.unpack('<I', file.read(4))
    print('     Num Channel Bindings: %i' % num_bindings)

    for i in range(num_bindings):
        (source, dest) = struct.unpack('<2B', file.read(2))
        print('      Channel binding %i -> %i' % (source, dest))
    align(file, 4)

    parse_x4(file, 'SourceMap', indent=5)

def parse_keywords(file, name_dict):
    (num_keywords,) = struct.unpack('<I', file.read(4))
    for i in range(num_keywords):
        (idx,) = struct.unpack('<H', file.read(2))
        print('     Keyword: %s' % name_dict[idx])

def parse_vector_params(file, name_dict, indent=5):
    num = parse_u4(file, 'Num Vectors', indent=indent)
    for i in range(num):
        (NameIndex, Index, ArraySize, Type, Dim) = struct.unpack('<IIIBB', file.read(14))
        print('%s Name: %s Index: %i ArraySize: %i Type: %i Dim: %i' %
                (' ' * indent, name_dict[NameIndex], Index, ArraySize, Type, Dim))
        align(file, 4)

def parse_matrix_params(file, name_dict, indent=5):
    num = parse_u4(file, 'Num Matrices', indent=indent)
    for i in range(num):
        (NameIndex, Index, ArraySize, Type, RowCount) = struct.unpack('<IIIBB', file.read(14))
        print('%s Name: %s Index: %i ArraySize: %i Type: %i RowCount: %i' %
                (' ' * indent, name_dict[NameIndex], Index, ArraySize, Type, RowCount))
        align(file, 4)

def parse_texture_params(file, name_dict, indent=5):
    num = parse_u4(file, 'Num Textures', indent=indent)
    for i in range(num):
        (NameIndex, Index, SamplerIndex, Dim) = struct.unpack('<IIIB', file.read(13))
        print('%s Name: %s Index: %i SamplerIndex: %i Dim: %i' %
                (' ' * indent, name_dict[NameIndex], Index, SamplerIndex, Dim))
        align(file, 4)

def parse_buffer_params(file, name_dict, indent=5):
    num = parse_u4(file, 'Num Buffers', indent=indent)
    for i in range(num):
        (NameIndex, Index) = struct.unpack('<II', file.read(8))
        print('      %s: %i' % (name_dict[NameIndex], Index))

def parse_cb_params(file, name_dict):
    num = parse_u4(file, 'Num Constant Buffers', indent=5)
    for i in range(num):
        print('     Constant Buffer %i' % i)
        NameIndex = parse_u4(file)
        print('      Name: %s' % name_dict[NameIndex])
        parse_matrix_params(file, name_dict, indent=6)
        parse_vector_params(file, name_dict, indent=6)
        Size = parse_u4(file, 'Size', indent=6)

def parse_cb_bindings(file, name_dict):
    num = parse_u4(file, 'Num Constant Buffer Bindings', indent=5)
    for i in range(num):
        (NameIndex, Index) = struct.unpack('<II', file.read(8))
        print('      %s: %i' % (name_dict[NameIndex], Index))

def parse_uav_params(file, name_dict):
    num = parse_u4(file, 'Num UAVs', indent=5)
    for i in range(num):
        print('     UAV %i' % i)
        (NameIndex, Index, OriginalIndex) = struct.unpack('<3I', file.read(12))
        print('      %s: %i %i' % (name_dict[NameIndex], Index, OriginalIndex))

def parse_subprograms(file, subprogram_type, name_dict):
    print('   %s:' % subprogram_type)
    num_subprograms = parse_u4(file, 'Num Subprograms')
    for i in range(num_subprograms):
        print('    Subprogram %i:' % i)
        parse_x4(file, 'BlobIndex', indent=5)
        parse_channels(file)
        parse_keywords(file, name_dict)
        (ShaderHardwareTier, GpuProgramType) = struct.unpack('<2B', file.read(2))
        print('     ShaderHardwareTier: %i' % ShaderHardwareTier)
        print('     GpuProgramType: %i' % GpuProgramType)
        align(file, 4)

        parse_vector_params(file, name_dict)
        parse_matrix_params(file, name_dict)
        parse_texture_params(file, name_dict)
        parse_buffer_params(file, name_dict)
        parse_cb_params(file, name_dict)
        parse_cb_bindings(file, name_dict)
        parse_uav_params(file, name_dict)

def parse_pass(file):
    name_dict = parse_name_indices_table(file)

    (type,) = struct.unpack('<I', file.read(4))
    assert(type == 0)

    parse_state(file)

    parse_x4(file, 'ProgramMask', indent=3)

    parse_subprograms(file, 'progVertex', name_dict)
    parse_subprograms(file, 'progFragment', name_dict)
    parse_subprograms(file, 'progGeometry', name_dict)
    parse_subprograms(file, 'progHull', name_dict)
    parse_subprograms(file, 'progDomain', name_dict)

    parse_byte(file, 'hasInstancingVariant', indent=3)
    align(file, 4)
    UseName = parse_string(file)
    Name = parse_string(file)
    TextureName = parse_string(file)
    print('   UseName: %s' % UseName)
    print('   Name: %s' % Name)
    print('   TextureName: %s' % TextureName)
    parse_tags(file)

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

        parse_tags(file, indent=2)
        parse_u4(file, 'LOD', indent=2)

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
