#!/usr/bin/env python3

# Port of shadertool to DX11. I thought long and hard about adapting shadertool
# to work with both, but eventually decided to make a clean start since there
# are quite a few differences between DX9 and DX11 shaders, and this way I
# could take a clean slate with some of the lessons learned working on
# shadertool and hlsltool and have cleaner code from the beginning. Some code
# from shadertool and hlsltool is still reused. Like hlsltool this is intended
# to use an approach based purely on pattern matching instead of the parser in
# shadertool, which may not be as powerful, but should be simpler.

import sys, os, re, collections, argparse, itertools, copy

import shadertool, hlsltool

from shadertool import debug, debug_verbose, component_set_to_string
from shadertool import vanity_comment, tool_name, expand_wildcards
from shadertool import game_git_dir, collected_errors, show_collected_errors
from hlsltool import cb_offset, cb_matrix

cbuffer_entry_pattern_cache = {}
def cbuffer_entry_pattern(type, name):
    try:
        return cbuffer_entry_pattern_cache[(type, name)]
    except KeyError:
        pattern = re.compile(r'''
            ^ \s* // \s*
            {0} \s+ {1};
            \s* // \s*
            Offset: \s+ (?P<offset>\d+)
            \s+
            Size: \s+ (?P<size>\d+)
            (?: \s+ \[unused\] )?
            \s* $
        '''.format(type, name), re.VERBOSE | re.MULTILINE)
        cbuffer_entry_pattern_cache[(type, name)] = pattern
        return pattern

resource_bind_pattern_cache = {}
def resource_bind_pattern(name, type=None, format=None, dim=None):
    try:
        return resource_bind_pattern_cache[name]
    except KeyError:
        pattern = re.compile(r'''
            ^ \s* //
            \s* {0} (?#name)
            \s+ {1} (?#type)
            \s+ {2} (?#format)
            \s+ {3} (?#dim)
            \s+ (?P<slot>\d+)
            \s+ (?P<elements>\d+)
            \s* $
        '''.format(
            name,
            type or r'(?P<type>\S+)',
            format or r'(?P<format>\S+)',
            dim or r'(?P<dim>\S+)'
        ), re.VERBOSE | re.MULTILINE)
        resource_bind_pattern_cache[name] = pattern
        return pattern

def cbuffer_bind_pattern(cb_name):
    return resource_bind_pattern(cb_name, 'cbuffer', 'NA', 'NA')

cbuffer_pattern = re.compile(r'// cbuffer (?P<name>.+)\n// {$', re.MULTILINE)

class Instruction(hlsltool.Instruction):
    pattern = re.compile(r'''
        \s*
        \S
        .*
        $
    ''', re.MULTILINE | re.VERBOSE)

class AssignmentInstruction(hlsltool.AssignmentInstruction, Instruction):
    pattern = re.compile(r'''
        \s*
        (?P<instruction>\S+)
        \s+
        (?P<lval>\S+)
        \s*
        ,
        \s*
        (?P<rval>\S.*)
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE)

    def __init__(self, text, instruction, lval, rval):
        hlsltool.AssignmentInstruction.__init__(self, text, lval, rval)
        self.instruction = instruction

    def is_noop(self):
        return False

class ResourceLoadInstruction(AssignmentInstruction):
    pattern = re.compile(r'''
        \s*
        (?P<instruction>[a-zA-Z_]+
            \s*
            \(
                [^)]+
            \)
            \(
                [^)]+
            \)
        )
        \s*
        (?P<lval>\S+)
        \s* , \s*
        (?P<rval>\S.*)
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE)

class SampleLIndexableInstruction(ResourceLoadInstruction):
    pattern = re.compile(r'''
        \s*
        (?P<instruction>sample_l_indexable
            \s*
            \(
                [^)]+
            \)
            \(
                [^)]+
            \)
        )
        \s*
        (?P<lval>\S+)
        \s* , \s*
        (?P<rval>
            (?P<arg1>\S+)
            \s* , \s*
            (?P<arg2>\S+)
            \s* , \s*
            (?P<arg3>\S+)
            \s* , \s*
            (?P<arg4>\S+)
        )
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE)

    def __init__(self, text, instruction, lval, rval, arg1, arg2, arg3, arg4):
        AssignmentInstruction.__init__(self, text, instruction, lval, rval)
        self.rargs = tuple(map(lambda x: hlsltool.expression_as_single_register(x) or x, (arg1, arg2, arg3, arg4)))

class DP4Instruction(AssignmentInstruction):
    pattern = re.compile(r'''
        \s*
        (?P<instruction>dp4)
        \s+
        (?P<lval>\S+)
        \s* , \s*
        (?P<rval>
            (?P<arg1>\S+)
            \s* , \s*
            (?P<arg2>\S+)
        )
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE)

    def __init__(self, text, instruction, lval, rval, arg1, arg2):
        AssignmentInstruction.__init__(self, text, instruction, lval, rval)
        self.rargs = tuple(map(lambda x: hlsltool.expression_as_single_register(x) or x, (arg1, arg2)))

class Declaration(Instruction):
    pattern = re.compile(r'''
        \s*
        dcl_.*
        $
    ''', re.MULTILINE | re.VERBOSE)

class ICBDeclaration(Declaration):
    pattern = re.compile(r'''
        \s*
        dcl_immediateConstantBuffer
        \s*
            \{
                .*
            \}
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE | re.DOTALL)

class TempsDeclaration(Declaration):
    pattern = re.compile(r'''
        \s*
        dcl_temps
        \s+
        (?P<temps>\d+)
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE)

    def __init__(self, text, temps):
        Declaration.__init__(self, text)
        self.temps = int(temps)

    def __str__(self):
        return '\ndcl_temps %d' % self.temps

class SVOutputDeclaration(Declaration):
    pattern = re.compile(r'''
        \s*
        dcl_output_s[ig]v
        \s+
        (?P<register>o[^,]+)
        \s*
        ,
        \s*
        (?P<system_value>\S+)
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE)

    def __init__(self, text, register, system_value):
        Declaration.__init__(self, text)
        self.register = hlsltool.expression_as_single_register(register)
        self.system_value = system_value

class ReturnInstruction(Instruction):
    pattern = re.compile(r'''
        \s*
        ret
        .*
        $
    ''', re.MULTILINE | re.VERBOSE)

specific_instructions = (
    ICBDeclaration,
    TempsDeclaration,
    SVOutputDeclaration,
    Declaration,
    ReturnInstruction,
    SampleLIndexableInstruction,
    ResourceLoadInstruction,
    DP4Instruction,
    AssignmentInstruction,
)

class ASMShader(hlsltool.Shader):
    shader_model_pattern = re.compile(r'^[vhdgpc]s_[45]_[01]$', re.MULTILINE)

    def __init__(self, filename):
        hlsltool.Shader.__init__(self, filename, args)

        self.temps = None
        self.early_insert_pos = 0

        self.shader_model_match = self.shader_model_pattern.search(self.text)
        self.shader_model = self.shader_model_match.group()

        self.declarations_txt = self.text[:self.shader_model_match.start()]
        body_txt = self.text[self.shader_model_match.end() : ]

        self.split_instructions(body_txt)
        self.process_declarations()

    def InstructionFactory(self, text, pos):
        match = hlsltool.Comment.pattern.match(text, pos)
        if match is not None:
            return hlsltool.Comment(match.group()), match.end()

        for specific_instruction in specific_instructions:
            match = specific_instruction.pattern.match(text, pos)
            if match is not None:
                return specific_instruction(match.group(), **match.groupdict()), match.end()

        match = Instruction.pattern.match(text, pos)
        if match is not None:
            return Instruction(match.group()), match.end()

        return None, pos

    def process_declarations(self):
        self.declarations = []
        self.sv_outputs = {}

        while self.instructions:
            instruction = self.instructions[0]
            if not isinstance(instruction, (Declaration, hlsltool.Comment)):
                break
            self.declarations.append(self.instructions.pop(0))

            if isinstance(instruction, TempsDeclaration):
                if self.temps:
                    raise SyntaxError("Bad shader: Multiple dcl_temps: %s" % instruction)
                self.temps = instruction
            elif isinstance(instruction, SVOutputDeclaration):
                self.sv_outputs[instruction.system_value] = instruction

        for instruction in self.instructions:
            if isinstance(instruction, Declaration):
                raise SyntaxError("Bad shader: Mixed declarations with code: %s" % instruction)

    def find_reg_from_column_major_matrix_multiply(self, cb):
        results = self.scan_shader(cb, write=False, instr_type=DP4Instruction)
        if len(results) != 1:
            debug_verbose(0, '%s read from %i instructions (only exactly 1 read currently supported)' % (cb, len(results)))
            return None
        (line, instr) = results[0]

        if instr.rargs[0].variable == cb:
            reg = instr.rargs[1]
        elif instr.rargs[1].variable == cb:
            reg = instr.rargs[0]
        else:
            assert(False)

        return reg, line

    def lookup_output_position(self):
        return self.sv_outputs['position'].register.variable

    def effective_swizzle(self, mask, swizzle):
        if mask and not swizzle:
            return mask
        swizzle4 = swizzle + swizzle[-1] * (4-len(swizzle))
        if not mask:
            return swizzle4
        ret = ''
        for component in mask:
            ret += {
                'x': swizzle4[0],
                'y': swizzle4[1],
                'z': swizzle4[2],
                'w': swizzle4[3],
            }[component]
        return ret

    def find_cb_entry(self, type, name):
        match = self.find_header(cbuffer_entry_pattern(type, name))
        debug_verbose(2, match.group())
        offset = int(match.group('offset'))

        pos = self.declarations_txt.rfind('// cbuffer ', 0, match.start())
        if pos == -1:
            raise KeyError()
        match = cbuffer_pattern.match(self.declarations_txt, pos)
        if match is None:
            raise KeyError()

        cb_name = match.group('name')
        # TODO: cb_size = find last offset + size

        match = cbuffer_bind_pattern(cb_name).search(self.declarations_txt, pos)
        if match is None:
            raise KeyError()
        debug_verbose(2, match.group())

        cb = int(match.group('slot'))

        # TODO: self.adjust_cb_size(cb, cb_size)
        return cb, offset

    def find_texture(self, name, type='texture', format=None, dim=None):
        match = self.find_header(resource_bind_pattern(name, type, format, dim))
        return 't' + match.group('slot')

    def insert_instr(self, pos, instruction=None, comment=None):
        off = 0
        if comment is not None:
            self.instructions.insert(pos + off, hlsltool.Comment('\n// %s' % comment))
            off += 1
        if instruction is not None:
            self.instructions.insert(pos + off, Instruction('\n' + instruction))
            off += 1
        if comment is None and instruction is None:
            self.instructions.insert(pos + off, hlsltool.Comment('\n'))
            off += 1
        return off

    def insert_decl(self, declaration=None, comment=None):
        if comment is not None:
            self.declarations.append(hlsltool.Comment('\n// %s' % comment))
        if declaration is not None:
            self.declarations.append(Declaration('\n' + declaration))
        if comment is None and declaration is None:
            self.declarations.append(hlsltool.Comment('\n'))

    def allocate_temp_reg(self):
        if self.temps is None:
            self.temps = TempsDeclaration('dcl_temps 0')
            self.declarations.append(self.temps)
        temp = self.temps.temps
        self.temps.temps += 1
        return 'r%d' % temp

    def insert_stereo_params(self):
        if self.inserted_stereo_params:
            return 0
        self.inserted_stereo_params = True
        self.stereo_params_reg = self.allocate_temp_reg()
        self.insert_decl()
        self.insert_decl('dcl_resource_texture2d (float,float,float,float) t125', '3DMigoto StereoParams:')
        off  = self.early_insert_instr()
        off += self.early_insert_instr('ld_indexable(texture2d)(float,float,float,float) {0}.xyzw, l(0, 0, 0, 0), t125.xyzw'.format(self.stereo_params_reg))
        off += self.early_insert_instr()
        return off

    def insert_halo_fix_code(self, pos, temp_reg):
        off = 0
        off += self.insert_instr(pos + off, 'ne {0}.w, {1}.w, l(1.0)'.format(self.stereo_params_reg, temp_reg.variable))
        off += self.insert_instr(pos + off, 'if_nz {0}.w'.format(self.stereo_params_reg))
        off += self.insert_instr(pos + off, '  add {0}.w, {1}.w, -{0}.y'.format(self.stereo_params_reg, temp_reg.variable))
        off += self.insert_instr(pos + off, '  mad {1}.x, {0}.w, {0}.x, {1}.x'.format(self.stereo_params_reg, temp_reg.variable))
        off += self.insert_instr(pos + off, 'endif')
        return off

    def __str__(self):
        s = self.declarations_txt
        s += self.shader_model_match.group()
        for instr in self.declarations:
            s += str(instr)
        for instr in self.instructions:
            s += str(instr)
        return s

def fix_fcprimal_reflection(shader):
    try:
        WaterReflectionTransform = cb_matrix(*shader.find_cb_entry('float4x4', 'WaterReflectionTransform'))
        refl_texture = shader.find_texture('ReflectionRealTexture__TexObj__', format='float4', dim='2d')
        ViewProjectionMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'ViewProjectionMatrix'))
        InvProjectionMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'InvProjectionMatrix'))
        InvViewMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'InvViewMatrix'))
    except KeyError:
        debug_verbose(0, 'Shader does not have all required values for the Far Cry Primal reflection fix')
        return

    (wpos, transform_line) = shader.find_reg_from_column_major_matrix_multiply(WaterReflectionTransform[0])
    assert(wpos.components == 'xyzw')

    results = shader.scan_shader(refl_texture, write=False)
    assert(len(results) == 1)
    (refl_line, refl_instr) = results[0]

    off = shader.insert_stereo_params()
    tmp1 = shader.allocate_temp_reg()
    tmp2 = shader.allocate_temp_reg()

    off += shader.insert_vanity_comment(transform_line + off, 'Far Cry Primal Reflection Fix inserted with')
    off += shader.insert_instr(transform_line + off)
    off += shader.insert_instr(transform_line + off, comment='ViewProjectionMatrix:')
    off += shader.insert_instr(transform_line + off, 'dp4 {0}.w, {1}.xyzw, {2}.xyzw'.format(
        shader.stereo_params_reg, wpos.variable, ViewProjectionMatrix[3]))
    off += shader.insert_instr(transform_line + off, comment='Stereo Correction:')
    off += shader.insert_instr(transform_line + off, 'add {0}.w, {0}.w, -{0}.y'.format(shader.stereo_params_reg))
    off += shader.insert_instr(transform_line + off, 'mul {0}.x, {1}.w, {1}.x'.format(tmp1, shader.stereo_params_reg))
    off += shader.insert_instr(transform_line + off, 'mov {0}.yzw, l(0.0)'.format(tmp1))
    off += shader.insert_instr(transform_line + off, comment='InvProjectionMatrix:')
    off += shader.insert_instr(transform_line + off, 'dp4 {0}.x, {1}.xyzw, {2}.xyzw'.format(tmp2, tmp1, InvProjectionMatrix[0]))
    off += shader.insert_instr(transform_line + off, 'dp4 {0}.y, {1}.xyzw, {2}.xyzw'.format(tmp2, tmp1, InvProjectionMatrix[1]))
    off += shader.insert_instr(transform_line + off, 'dp4 {0}.z, {1}.xyzw, {2}.xyzw'.format(tmp2, tmp1, InvProjectionMatrix[2]))
    off += shader.insert_instr(transform_line + off, 'dp4 {0}.w, {1}.xyzw, {2}.xyzw'.format(tmp2, tmp1, InvProjectionMatrix[3]))
    off += shader.insert_instr(transform_line + off, comment='InvViewMatrix:')
    off += shader.insert_instr(transform_line + off, 'dp4 {0}.x, {1}.xyzw, {2}.xyzw'.format(tmp1, tmp2, InvViewMatrix[0]))
    off += shader.insert_instr(transform_line + off, 'dp4 {0}.y, {1}.xyzw, {2}.xyzw'.format(tmp1, tmp2, InvViewMatrix[1]))
    off += shader.insert_instr(transform_line + off, comment='Negate Z to fix alignment when camera is tilted:')
    off += shader.insert_instr(transform_line + off, 'dp4 {0}.z, -{1}.xyzw, {2}.xyzw'.format(tmp1, tmp2, InvViewMatrix[2]))
    off += shader.insert_instr(transform_line + off, comment='Adjust Coord:')
    off += shader.insert_instr(transform_line + off, 'add {0}.xyz, {0}.xyz, {1}.xyzw'.format(wpos.variable, tmp1))
    off += shader.insert_instr(transform_line + off)

    coord, texture, sampler, lod = refl_instr.rargs
    coord_x = coord.components[0]

    off += shader.insert_instr(refl_line + off)
    off += shader.insert_instr(refl_line + off, comment='Swap reflection eyes from stereo2mono reflection copy.')
    off += shader.insert_instr(refl_line + off, comment='Mip-maps disabled as the reverse stereo blit only copies them in one eye')
    off += shader.insert_instr(refl_line + off, 'mov {0}.xyzw, {1}.xyzw'.format(tmp1, coord.variable))
    off += shader.insert_instr(refl_line + off, 'mul {0}.{1}, {0}.{1}, l(0.5)'.format(tmp1, coord_x))
    off += shader.insert_instr(refl_line + off, 'eq {0}.w, {0}.z, l(-1.0)'.format(shader.stereo_params_reg))
    off += shader.insert_instr(refl_line + off, 'if_nz {0}.w'.format(shader.stereo_params_reg))
    off += shader.insert_instr(refl_line + off, '  add {0}.{1}, {0}.{1}, l(0.5)'.format(tmp1, coord_x))
    off += shader.insert_instr(refl_line + off, 'endif')
    off += shader.insert_instr(refl_line + off)
    shader.comment_out_instruction(refl_line + off)
    shader.insert_decl('dcl_resource_texture2d (float,float,float,float) t100', 'stereo2mono copy of %s:' % texture.variable)
    off += shader.insert_instr(refl_line + off + 1, '{0} {1}, {2}.{3}, t100.xyzw, {4}, l(0.0)'.format(
        refl_instr.instruction, refl_instr.lval, tmp1, coord.components, sampler.variable))
    off += shader.insert_instr(refl_line + off + 1)

    shader.set_ini_name('Reflection')
    shader.add_shader_override_setting('ps-t100 = stereo2mono ps-{0}'.format(texture.variable))
    shader.add_shader_override_setting('post ps-t100 = null')

    shader.autofixed = True

def fix_fcprimal_physical_lighting(shader):
    if shader.shader_type != 'cs':
        debug_verbose(0, 'Far Cry Primal physical lighting fix only applies to compute shaders')
        return
    try:
        Depth = shader.find_texture('Depth', format='float', dim='2d')
        DepthScale = cb_offset(*shader.find_cb_entry('float4', 'DepthScale'))
        CameraDistances = cb_offset(*shader.find_cb_entry('float4', 'CameraDistances'))
        InvViewProjection = cb_matrix(*shader.find_cb_entry('float4x4', 'InvViewProjection'))
    except KeyError:
        debug_verbose(0, 'Shader does not have all required values for the Far Cry Primal physical lighting fix')
        return

    (spos, ivp_line) = shader.find_reg_from_column_major_matrix_multiply(InvViewProjection[0])
    assert(spos.components == 'xyzw')

    results = shader.scan_shader(Depth, write=False)
    assert(len(results) == 1)
    (depth_line, depth_instr) = results[0]
    depth_reg = hlsltool.expression_as_single_register(depth_instr.lval)

    off = shader.insert_stereo_params()

    off += shader.insert_instr(depth_line + off)
    off += shader.insert_instr(depth_line + 1 + off)
    off += shader.insert_instr(depth_line + 1 + off, comment='Use DepthScale & CameraDistances.z to get world Z:')
    off += shader.insert_instr(depth_line + 1 + off, 'mad {0}.z, {1}.{2}, {3}.y, {3}.x'.format(
        shader.stereo_params_reg, depth_reg.variable, depth_reg.components[0], DepthScale))
    off += shader.insert_instr(depth_line + 1 + off, 'div {0}.z, l(1.0), {0}.z'.format(shader.stereo_params_reg))
    off += shader.insert_instr(depth_line + 1 + off, 'mul {0}.z, {0}.z, {1}.z'.format(shader.stereo_params_reg, CameraDistances))
    off += shader.insert_instr(depth_line + 1 + off)

    off += shader.insert_vanity_comment(ivp_line + off, 'Far Cry Primal Physical Lighting Fix inserted with')
    off += shader.insert_instr(ivp_line + off, 'add {0}.w, {0}.z, -{0}.y'.format(shader.stereo_params_reg))
    off += shader.insert_instr(ivp_line + off, 'div {0}.w, {0}.w, {0}.z'.format(shader.stereo_params_reg))
    off += shader.insert_instr(ivp_line + off, 'mad {0}.x, {1}.w, -{1}.x, {0}.x'.format(spos.variable, shader.stereo_params_reg))
    off += shader.insert_instr(ivp_line + off)

    shader.autofixed = True

def fix_fcprimal_camera_pos(shader):
    try:
        CameraPosition = cb_offset(*shader.find_cb_entry('float3', 'CameraPosition'))
        InvProjectionMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'InvProjectionMatrix'))
        InvViewMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'InvViewMatrix'))
    except KeyError:
        debug_verbose(0, 'Shader does not declare all required values for the Far Cry Primal camera position adjustment')
        return

    results = shader.scan_shader(CameraPosition, write=False)
    if not results:
        debug_verbose(0, 'Shader does not use CameraPosition')
        return

    off = shader.insert_stereo_params()
    tmp1 = shader.allocate_temp_reg()
    tmp2 = shader.allocate_temp_reg()

    off += shader.early_insert_vanity_comment('Camera Position (environment reflections, etc) adjustment inserted with')
    shader.early_insert_instr('mul {0}.x, {1}.x, {1}.y'.format(tmp1, shader.stereo_params_reg))
    shader.early_insert_instr('mul {0}.x, {0}.x, {1}.x'.format(tmp1, InvProjectionMatrix[0]))
    shader.early_insert_instr('mov {0}.yzw, l(0.0)'.format(tmp1))

    shader.early_insert_instr('dp4 {0}.x, {1}.xyzw, {2}.xyzw'.format(tmp2, tmp1, InvViewMatrix[0]))
    shader.early_insert_instr('dp4 {0}.y, {1}.xyzw, {2}.xyzw'.format(tmp2, tmp1, InvViewMatrix[1]))
    shader.early_insert_instr('dp4 {0}.z, {1}.xyzw, {2}.xyzw'.format(tmp2, tmp1, InvViewMatrix[2]))

    shader.replace_reg(CameraPosition, tmp1, 'xyz')
    shader.early_insert_instr('mov {0}.xyzw, {1}.xyzw'.format(tmp1, CameraPosition))
    shader.early_insert_instr('add {0}.xyz, {0}.xyz, {1}.xyz'.format(tmp1, tmp2))
    shader.early_insert_instr()

    shader.autofixed = True

def parse_args():
    global args

    parser = argparse.ArgumentParser(description = 'nVidia 3D Vision DX11 Assembly Shaderhacker Tool')
    parser.add_argument('files', nargs='+',
            help='List of assembly files to process')

    parser.add_argument('--install', '-i', action='store_true',
            help='Install shaders in ShaderFixes directory')
    parser.add_argument('--install-to', '-I',
            help='Install shaders under ShaderOverride in a custom directory')
    parser.add_argument('--to-git', '--git', action='store_true',
            help='Copy the file to the location of this script, guessing the name of the game. Implies --no-convert and --force')
    parser.add_argument('--force', '-f', action='store_true',
            help='Forcefully overwrite shaders when installing')
    parser.add_argument('--output', '-o', type=argparse.FileType('w'),
            help='Save the shader to a file')
    parser.add_argument('--in-place', action='store_true',
            help='Overwrite the file in-place')

    parser.add_argument('--auto-fix-vertex-halo', action='store_true',
            help="Attempt to automatically fix a vertex shader for common halo type issues")
    parser.add_argument('--fix-fcprimal-reflection', action='store_true',
            help="Fix a reflection shader in Far Cry Primal")
    parser.add_argument('--fix-fcprimal-physical-lighting', action='store_true',
            help="Fix a physical lighting compute shader in Far Cry Primal")
    parser.add_argument('--fix-fcprimal-camera-pos', action='store_true',
            help="Fix reflections, specular highlights, etc. by adjusting the camera position in Far Cry Primal")
    parser.add_argument('--only-autofixed', action='store_true',
            help="Installation type operations only act on shaders that were successfully autofixed with --auto-fix-vertex-halo")

    parser.add_argument('--ignore-other-errors', action='store_true',
            help='Continue with the next file in the event of some other error while applying a fix')

    parser.add_argument('--verbose', '-v', action='count', default=0,
            help='Level of verbosity')
    parser.add_argument('--quiet', '-q', action='count', default=0,
            help='Suppress usual informational messages. Specify multiple times to suppress more messages.')

    args = parser.parse_args()

    if not args.output and not args.in_place and not args.install and not \
            args.install_to and not args.to_git:
        parser.error("did not specify anything to do (e.g. --install, --install-to, --in-place, --output, --show-regs, etc)");

    shadertool.verbosity = args.verbose - args.quiet

def main():
    parse_args()
    shadertool.expand_wildcards(args)
    for file in args.files:
        debug_verbose(-2, 'parsing %s...' % file)
        shader = ASMShader(file)

        try:
            if args.auto_fix_vertex_halo:
                hlsltool.auto_fix_vertex_halo(shader)
            if args.fix_fcprimal_reflection:
                fix_fcprimal_reflection(shader)
            if args.fix_fcprimal_physical_lighting:
                fix_fcprimal_physical_lighting(shader)
            if args.fix_fcprimal_camera_pos:
                fix_fcprimal_camera_pos(shader)
        except Exception as e:
            if args.ignore_other_errors:
                collected_errors.append((file, e))
                import traceback, time
                traceback.print_exc()
                continue
            raise

        real_file = file
        #if args.original:
        #    file = find_original_shader(file)

        if not args.only_autofixed or shader.autofixed:
            if args.output:
                print(shader, end='', file=args.output)
                shader.update_ini()
            if args.in_place:
                tmp = '%s.new' % real_file
                print(shader, end='', file=open(tmp, 'w'))
                os.rename(tmp, real_file)
                shader.update_ini()
            if args.install:
                if hlsltool.install_shader(shader, file, args):
                    shader.update_ini()
                    pass
            if args.install_to:
                if hlsltool.install_shader_to(shader, file, args, os.path.expanduser(args.install_to), True):
                    shader.update_ini()
                    pass
            if args.to_git:
                a = copy.copy(args)
                a.force = True
                if hlsltool.install_shader_to_git(shader, file, a):
                    shader.update_ini()
    show_collected_errors()
    hlsltool.do_ini_updates()

if __name__ == '__main__':
    main()

# vi: et ts=4:sw=4
