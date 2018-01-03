#!/usr/bin/env python3

import sys, os, argparse, glob, struct, zlib, itertools, io
import extract_unity_shaders, extract_unity53_shaders
from unity_asset_extractor import lz4_decompress

def pr_verbose(*a, verbosity=1, **kw):
    if args.verbose >= verbosity:
        print(*a, **kw)

# Data structure we manufacture to create classic Unity style headers. For now
# we only create fairly minimal headers with the information we need later,
# such as Tags to detect SHADOWCASTERs. We also skip some information like
# bindings that is redundantly available in the 5.3 style headers.

class UnnamedTree(object):
    @property
    def parent_counter_attr(self):
        return '%s_counter' % self.keyword

    @property
    def parent_counter(self):
        return getattr(self.parent, self.parent_counter_attr, 0)

    @parent_counter.setter
    def parent_counter(self, val):
        return setattr(self.parent, self.parent_counter_attr, val)

    def __init__(self, parent):
        self.parent = parent
        self.parent_counter += 1
        self.counter = self.parent_counter

    def header(self):
        return '%s %i/%i {' % (self.__class__.__name__, self.counter, self.parent_counter)

    def __iter__(self):
        return iter([])

class NamedTree(object):
    def header(self):
        return '%s "%s" {' % (self.__class__.__name__, self.name)

    def __iter__(self):
        return iter([])

class Shader(NamedTree):
    keyword = 'Shader'
    parent = None

    @property
    def filename(self):
        return safe_filename(self.name)

    def __iter__(self):
        if self.CustomEditorName:
            yield 'CustomEditor "%s"' % self.CustomEditorName
        if self.FallbackName:
            yield 'Fallback "%s"' % self.FallbackName

class SubShader(UnnamedTree):
    keyword = 'SubShader'
    def __init__(self, parent):
        UnnamedTree.__init__(self, parent)

    def __iter__(self):
        if self.lod:
            yield 'LOD %i' % self.lod
        if self.tags is not None:
            yield self.tags

class Pass(UnnamedTree):
    keyword = 'Pass'
    def __init__(self, parent):
        UnnamedTree.__init__(self, parent)

    def __iter__(self):
        # TODO: if self.lod:
        # TODO:     yield 'LOD %i' % self.lod
        if self.name:
            yield 'Name "%s"' % self.name

        if self.tags is not None:
            yield self.tags
        if self.tags1 is not None:
            yield self.tags1

        # Not positive this is right, but seems likely:
        if self.ZWrite[1] != '<noninit>':
            yield 'ZWrite [%s]' % self.ZWrite[1]
        elif not self.ZWrite[0]:
            yield 'ZWrite Off'

class Program(NamedTree):
    keyword = 'Program'
    def __init__(self, parent, name):
        self.parent = parent
        self.name = name
class SubProgram(NamedTree):
    keyword = 'SubProgram'
    def __init__(self, parent, name):
        self.parent = parent
        self.name = name

def align(file, alignment):
    off = file.tell()
    mod = off % alignment
    if mod == 0:
        return
    data = file.read(alignment - mod)
    assert(data == b'\0' * (alignment - mod))

def parse_string(file, name=None, indent=0):
    (length,) = struct.unpack('<I', file.read(4))
    string = file.read(length).decode('ascii')
    align(file, 4)
    if name is not None:
        print_field(name, '%s' % string, indent=indent)
    return string

def parse_properties_table(file):
    (table_len,) = struct.unpack('<I', file.read(4))
    if table_len == 0:
        return

    pr_verbose('Properties {')
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
        pr_verbose('  {name} "{desc}" {num_attributes:x} {type:x} {flags:x} {def0} {def1} {def2} {def3} "{def_texture}" {texdim}'.format(
            name=name, desc=desc, num_attributes=num_attributes, type=type, flags=flags, def0=def0,
            def1=def1, def2=def2, def3=def3, def_texture=def_texture, texdim=texdim))
        if attributes:
            pr_verbose('    Attributes: ' + ', '.join(attributes))
    pr_verbose('}')

def parse_name_indices_table(file):
    (num_names,) = struct.unpack('<I', file.read(4))
    name_dict = {}

    for i in range(num_names):
        name = parse_string(file)
        (idx,) = struct.unpack('<I', file.read(4))
        assert(idx not in name_dict)
        name_dict[idx] = name
        pr_verbose('    Name[%i]: %s' % (idx, name))

    return name_dict

def print_state_entry(name1, val, name2, indent=4):
    pr_verbose('{indent}{name1:20}: {val} {name2}'.format(name1=name1, val=val, name2=name2, indent = ' ' * indent))
    #if name2 != '<noninit>':
    #    assert(name1 == name2)

def print_field(name, val, indent=4, verbosity=1):
    pr_verbose('{indent}{name:20}: {val}'.format(name=name, val=val, indent = ' ' * indent), verbosity=verbosity)

def parse_state_x4(file, verify_name, indent=4):
    (val,) = struct.unpack('<I', file.read(4))
    name = parse_string(file)
    print_state_entry(verify_name, '0x%08x' % val, name, indent=indent)

def parse_state_float(file, verify_name, indent=4):
    (val,) = struct.unpack('<f', file.read(4))
    name = parse_string(file)
    print_state_entry(verify_name, '%.9g' % val, name, indent=indent)
    return val, name

def parse_rt_blend_state(file, rt):
    pr_verbose('   RT Blend State[%i]:' % rt)
    parse_state_float(file, 'srcBlend', indent=4)
    parse_state_float(file, 'destBlend', indent=4)
    parse_state_float(file, 'srcBlendAlpha', indent=4)
    parse_state_float(file, 'destBlendAlpha', indent=4)
    parse_state_float(file, 'blendOp', indent=4)
    parse_state_float(file, 'blendOpAlpha', indent=4)
    parse_state_float(file, 'colMask', indent=4)

def parse_stencil_op_state(file, op):
    pr_verbose('   %s:' % op)
    parse_state_float(file, 'pass', indent=4)
    parse_state_float(file, 'fail', indent=4)
    parse_state_float(file, 'zFail', indent=4)
    parse_state_float(file, 'comp', indent=4)

def parse_state_color(file, name1):
    pr_verbose('   %s:' % name1)
    parse_state_float(file, 'x', indent=4)
    parse_state_float(file, 'y', indent=4)
    parse_state_float(file, 'z', indent=4)
    parse_state_float(file, 'w', indent=4)
    name2 = parse_string(file)
    pr_verbose('%s%s' % (' ' * 24, name2))

def parse_x4(file, name, indent=4):
    (val,) = struct.unpack('<I', file.read(4))
    print_field(name, '0x%08x' % val, indent=indent)
    return val

def parse_u4(file, name=None, indent=4, verbosity=1):
    (val,) = struct.unpack('<I', file.read(4))
    if name is not None:
        print_field(name, '%i' % val, indent=indent, verbosity=verbosity)
    return val

def parse_byte(file, name=None, indent=4):
    (val,) = struct.unpack('B', file.read(1))
    if name is not None:
        print_field(name, '%i' % val, indent=indent)
    return val

def parse_tags(file, indent=3):
    (num_pass_tags,) = struct.unpack('<I', file.read(4))
    if num_pass_tags:
        ret = 'Tags {'
        for i in range(num_pass_tags):
            ret += ' "%s"="%s"' % (parse_string(file), parse_string(file))
        ret += ' }'
        pr_verbose('%s%s' % (' ' * indent, ret))
        return ret

def parse_state(file, pass_info):
    pass_info.name = parse_string(file)
    pr_verbose('   State Name: %s' % pass_info.name)

    for rt in range(8):
        parse_rt_blend_state(file, rt)

    (rtSeparateBlend,) = struct.unpack('B', file.read(1))
    pr_verbose('   RT Separate Blend: %i' % rtSeparateBlend)
    align(file, 4)

    parse_state_float(file, 'zTest', indent=3)
    pass_info.ZWrite = parse_state_float(file, 'zWrite', indent=3)
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

    pass_info.tags = parse_tags(file)

    pass_info.lod = parse_u4(file, 'LOD', indent=3)
    parse_x4(file, 'lighting', indent=3)

def parse_channels(file):
    (num_bindings,) = struct.unpack('<I', file.read(4))
    pr_verbose('     Num Channel Bindings: %i' % num_bindings)

    for i in range(num_bindings):
        (source, dest) = struct.unpack('<2B', file.read(2))
        pr_verbose('      Channel binding %i -> %i' % (source, dest))
    align(file, 4)

    parse_x4(file, 'SourceMap', indent=5)

def parse_keywords(file, name_dict):
    (num_keywords,) = struct.unpack('<I', file.read(4))
    for i in range(num_keywords):
        (idx,) = struct.unpack('<H', file.read(2))
        pr_verbose('     Keyword: %s' % name_dict[idx])

def parse_vector_params(file, name_dict, indent=5):
    num = parse_u4(file, 'Num Vectors', indent=indent)
    for i in range(num):
        (NameIndex, Index, ArraySize, Type, Dim) = struct.unpack('<IIIBB', file.read(14))
        pr_verbose('%s Name: %s Index: %i ArraySize: %i Type: %i Dim: %i' %
                (' ' * indent, name_dict[NameIndex], Index, ArraySize, Type, Dim))
        align(file, 4)

def parse_matrix_params(file, name_dict, indent=5):
    num = parse_u4(file, 'Num Matrices', indent=indent)
    for i in range(num):
        (NameIndex, Index, ArraySize, Type, RowCount) = struct.unpack('<IIIBB', file.read(14))
        pr_verbose('%s Name: %s Index: %i ArraySize: %i Type: %i RowCount: %i' %
                (' ' * indent, name_dict[NameIndex], Index, ArraySize, Type, RowCount))
        align(file, 4)

def parse_texture_params(file, name_dict, indent=5):
    num = parse_u4(file, 'Num Textures', indent=indent)
    for i in range(num):
        (NameIndex, Index, SamplerIndex, Dim) = struct.unpack('<IIIB', file.read(13))
        pr_verbose('%s Name: %s Index: %i SamplerIndex: %i Dim: %i' %
                (' ' * indent, name_dict[NameIndex], Index, SamplerIndex, Dim))
        align(file, 4)

def parse_buffer_params(file, name_dict, indent=5):
    num = parse_u4(file, 'Num Buffers', indent=indent)
    for i in range(num):
        (NameIndex, Index) = struct.unpack('<II', file.read(8))
        pr_verbose('      %s: %i' % (name_dict[NameIndex], Index))

def parse_cb_params(file, name_dict):
    num = parse_u4(file, 'Num Constant Buffers', indent=5)
    for i in range(num):
        pr_verbose('     Constant Buffer %i' % i)
        NameIndex = parse_u4(file)
        pr_verbose('      Name: %s' % name_dict[NameIndex])
        parse_matrix_params(file, name_dict, indent=6)
        parse_vector_params(file, name_dict, indent=6)
        Size = parse_u4(file, 'Size', indent=6)

def parse_cb_bindings(file, name_dict):
    num = parse_u4(file, 'Num Constant Buffer Bindings', indent=5)
    for i in range(num):
        (NameIndex, Index) = struct.unpack('<II', file.read(8))
        pr_verbose('      %s: %i' % (name_dict[NameIndex], Index))

def parse_uav_params(file, name_dict):
    num = parse_u4(file, 'Num UAVs', indent=5)
    for i in range(num):
        pr_verbose('     UAV %i' % i)
        (NameIndex, Index, OriginalIndex) = struct.unpack('<3I', file.read(12))
        pr_verbose('      %s: %i %i' % (name_dict[NameIndex], Index, OriginalIndex))

def parse_programs(file, program_type, name_dict, pass_info, sub_programs):
    pr_verbose('   %s:' % program_type)
    program = Program(pass_info, program_type)
    num_subprograms = parse_u4(file, 'Num Subprograms')
    for i in range(num_subprograms):
        print('    Subprogram %s %i/%i:' % (program_type, i+1, num_subprograms))
        BlobIndex = parse_u4(file, 'BlobIndex', indent=5)
        parse_channels(file)
        parse_keywords(file, name_dict)
        (ShaderHardwareTier, GpuProgramType) = struct.unpack('<2B', file.read(2))
        pr_verbose('     ShaderHardwareTier: %i' % ShaderHardwareTier)
        pr_verbose('     GpuProgramType: %i' % GpuProgramType)
        align(file, 4)

        parse_vector_params(file, name_dict)
        parse_matrix_params(file, name_dict)
        parse_texture_params(file, name_dict)
        parse_buffer_params(file, name_dict)
        parse_cb_params(file, name_dict)
        parse_cb_bindings(file, name_dict)
        parse_uav_params(file, name_dict)

        sub_program = SubProgram(program, extract_unity53_shaders.get_shader_api(GpuProgramType)[0])
        if (BlobIndex, GpuProgramType) not in sub_programs:
            sub_programs[(BlobIndex, GpuProgramType)] = []
        sub_programs[(BlobIndex, GpuProgramType)].append(sub_program)

def parse_pass(file, sub_shader, sub_programs):
    pass_info = Pass(sub_shader)
    name_dict = parse_name_indices_table(file)

    type = parse_x4(file, 'Type', indent=3)

    parse_state(file, pass_info)

    parse_x4(file, 'ProgramMask', indent=3)

    parse_programs(file, 'vp', name_dict, pass_info, sub_programs)
    parse_programs(file, 'fp', name_dict, pass_info, sub_programs)
    parse_programs(file, 'gp', name_dict, pass_info, sub_programs)
    parse_programs(file, 'hp', name_dict, pass_info, sub_programs)
    parse_programs(file, 'dp', name_dict, pass_info, sub_programs)

    parse_byte(file, 'hasInstancingVariant', indent=3)
    align(file, 4)
    UseName = parse_string(file)
    Name = parse_string(file)
    TextureName = parse_string(file)
    pr_verbose('   UseName: %s' % UseName)
    pr_verbose('   Name: %s' % Name)
    pr_verbose('   TextureName: %s' % TextureName)

    # I don't know how these tags differ from those in parse_state, since they
    # both seem to apply to passes. LiSBtS has a shader asset containing both
    # tags fields set, but the pass with this particular tags field has no
    # subprograms (i.e. no shaders associated with it), so... I dunno???
    # DLC/E2/e2_s04_a.bytes/CAB-f8a9698b4eaca505856ce5da8de78688/0x08ac37e0.shader.raw
    pass_info.tags1 = parse_tags(file)

def parse_dependencies_1(file):
    num = parse_u4(file, 'Num Dependencies', indent=2)
    for i in range(num):
        dependency_from = parse_string(file)
        dependency_to = parse_string(file)
        pr_verbose('   from: %s to: %s' % (dependency_from, dependency_to))

def parse_dependencies_2(file):
    num = parse_u4(file, 'Num Dependencies', indent=2)
    for i in range(num):
        (FileID, PathID) = struct.unpack('<IQ', file.read(12))
        pr_verbose('   FileID: %i PathID: %i' % (FileID, PathID))

def parse_decompressed_blob(blob, filename, sub_programs):
    num_shaders = parse_u4(blob, 'Num shaders in blob', indent=3)
    shader_offsets = []
    for i in range(num_shaders):
        shader_offsets.append(struct.unpack('<2I', blob.read(8)))

    for i, (offset, length) in enumerate(shader_offsets):
        print('    Shader %i/%i:' % (i+1, num_shaders))
        sub_program = lambda shader_type: sub_programs[(i, shader_type)]
        extract_unity53_shaders.args = args
        extract_unity53_shaders.extract_shader_at(blob, offset, length, filename, sub_program, False)

def safe_filename(filename):
    filename = filename.replace('/', '_')
    # FIXME: Probably need to sanitise other characters
    return filename

def parse_unity55_shader(filename):
    file = open(filename, 'rb')
    shader = Shader()
    sub_programs = {}

    (asset_name_len,) = struct.unpack('<I', file.read(4))
    assert(asset_name_len == 0)

    parse_properties_table(file)

    (num_subshaders,) = struct.unpack('<I', file.read(4))
    pr_verbose('Number of subshaders: %i' % num_subshaders)
    for subshader in range(num_subshaders):
        print(' Subshader %i/%i:' % (subshader+1, num_subshaders))
        sub_shader = SubShader(shader)

        (num_passes,) = struct.unpack('<I', file.read(4))
        pr_verbose('  Number of passes: %i' % num_passes)
        for pass_no in range(num_passes):
            print('  Pass %i/%i:' % (pass_no+1, num_passes))
            parse_pass(file, sub_shader, sub_programs)

        sub_shader.tags = parse_tags(file, indent=2)
        sub_shader.lod = parse_u4(file, 'LOD', indent=2)

    shader.name = parse_string(file)
    shader.CustomEditorName = parse_string(file)
    shader.FallbackName = parse_string(file)
    print(' Name: %s' % shader.name)
    pr_verbose(' CustomEditorName: %s' % shader.CustomEditorName)
    pr_verbose(' FallbackName: %s' % shader.FallbackName)

    parse_dependencies_1(file)

    parse_byte(file, 'DisableNoSubshadersMessage', indent=1)
    align(file, 4)

    num_platforms = parse_u4(file, 'Num Platforms', indent=1, verbosity=0)
    platforms = []
    for i in range(num_platforms):
        platforms.append(parse_x4(file, 'Platform', indent=2))

    num_offsets = parse_u4(file, 'Num Offsets', indent=1)
    offsets = []
    for i in range(num_offsets):
        offsets.append(parse_x4(file, 'Offset', indent=2))

    num_compressed_lengths = parse_u4(file, 'Num Compressed Lengths', indent=1)
    compressed_lengths = []
    for i in range(num_compressed_lengths):
        compressed_lengths.append(parse_u4(file, 'Compressed Length', indent=2))

    num_decompressed_lengths = parse_u4(file, 'Num Decompressed Lengths', indent=1)
    decompressed_lengths = []
    for i in range(num_decompressed_lengths):
        decompressed_lengths.append(parse_u4(file, 'Decompressed Length', indent=2))

    assert(num_platforms == num_offsets == num_compressed_lengths == num_decompressed_lengths)

    num_compressed_bytes = parse_u4(file, 'Num Compressed Bytes', indent=1)
    assert(num_compressed_bytes == sum(compressed_lengths))
    compressed_blob = file.read(num_compressed_bytes)
    align(file, 4)

    parse_dependencies_2(file)
    parse_byte(file, 'ShaderIsBaked', indent=1)
    align(file, 4)
    assert(file.read(1) == b'') # Check whole resource was parsed

    for i in range(num_offsets):
        print('  Platform %i:' % platforms[i])
        blob = io.BytesIO(compressed_blob[offsets[i]:offsets[i]+compressed_lengths[i]])
        decompressed = lz4_decompress(blob, decompressed_lengths[i])
        parse_decompressed_blob(io.BytesIO(decompressed), shader.filename, sub_programs)

def parse_args():
    global args
    parser = argparse.ArgumentParser(description = 'Unity 5.5 Shader Extractor')
    parser.add_argument('shaders', nargs='+',
            help='List of compiled Unity shader files to parse')
    parser.add_argument('--type', action='append', choices=('d3d9', 'd3d11'),
            help='Filter types of shaders to process, useful to avoid unnecessary slow hash calculations')
    parser.add_argument('--verbose', '-v', action='count', default=0,
            help='Level of verbosity')
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

    extract_unity53_shaders.write_delayed_shaders()

if __name__ == '__main__':
    sys.exit(main())

# vi: sw=4:ts=4:expandtab
