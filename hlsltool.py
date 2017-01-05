#!/usr/bin/env python3

# Similar idea to shadertool, but whereas there I implemented a full assembly
# parser and logic to analyse instruction streams, this is intended to use an
# approach based purely on pattern matching instead, which may not be as
# powerful, but should be simpler. This relies on matching the particular's of
# 3DMigoto's HLSL decompiler and I don't intend to turn this into a full HLSL
# parser - I'd be better off porting shadertool to DX11 since assembly language
# is easier to reason about programatically than HLSL.

import sys, os, re, collections, argparse, itertools, copy, textwrap

import shadertool
from shadertool import debug, debug_verbose, component_set_to_string
from shadertool import vanity_comment, tool_name, expand_wildcards
from shadertool import game_git_dir, collected_errors, show_collected_errors

unity_ConstBuffer_pattern = re.compile(r'ConstBuffer\s"(?P<name>[^"]+)"\s(?P<size>[0-9]+)$', re.MULTILINE)
unity_BindCB_pattern = re.compile(r'BindCB\s"(?P<name>[^"]+)"\s(?P<cb>[0-9]+)$', re.MULTILINE)

# From CGIncludes/UnityShaderVariables.cginc:
# TODO: Allocate the register (avoid b12 used by the driver)
UnityPerDraw = '''
cbuffer UnityPerDraw : register(b11) {
	float4x4 glstate_matrix_mvp;
	float4x4 glstate_matrix_modelview0;
	float4x4 glstate_matrix_invtrans_modelview0;
	#define UNITY_MATRIX_MVP glstate_matrix_mvp
	#define UNITY_MATRIX_MV glstate_matrix_modelview0
	#define UNITY_MATRIX_IT_MV glstate_matrix_invtrans_modelview0

	uniform float4x4 _Object2World;
	uniform float4x4 _World2Object;
	uniform float4 unity_LODFade; // x is the fade value ranging within [0,1]. y is x quantized into 16 levels
	uniform float4 unity_WorldTransformParams; // w is usually 1.0, or -1.0 for odd-negative scale transforms
}
'''

UnityPerCamera = '''
cbuffer UnityPerCamera : register(b13)
{
	// Time (t = time since current level load) values from Unity
	uniform float4 _Time; // (t/20, t, t*2, t*3)
	uniform float4 _SinTime; // sin(t/8), sin(t/4), sin(t/2), sin(t)
	uniform float4 _CosTime; // cos(t/8), cos(t/4), cos(t/2), cos(t)
	uniform float4 unity_DeltaTime; // dt, 1/dt, smoothdt, 1/smoothdt

	uniform float3 _WorldSpaceCameraPos;

	// x = 1 or -1 (-1 if projection is flipped)
	// y = near plane
	// z = far plane
	// w = 1/far plane
	uniform float4 _ProjectionParams;

	// x = width
	// y = height
	// z = 1 + 1.0/width
	// w = 1 + 1.0/height
	uniform float4 _ScreenParams;

	// Values used to linearize the Z buffer (http://www.humus.name/temp/Linearize%20depth.txt)
	// x = 1-far/near
	// y = far/near
	// z = x/far
	// w = y/far
	uniform float4 _ZBufferParams;

	// x = orthographic camera's width
	// y = orthographic camera's height
	// z = unused
	// w = 1.0 if camera is ortho, 0.0 if perspective
	uniform float4 unity_OrthoParams;
}
'''

include_matrix_hlsl = '''
#include <matrix.hlsl>
'''

d3dx_ini = {}

class Instruction(object):
    pattern = re.compile(r'[^;]*;')

    def __init__(self, text):
        self.text = text
        self.rval = text

    def __str__(self):
        return self.text

    def strip(self):
        return str(self).strip()

    def writes(self, variable, components=None):
        return False

    def reads(self, variable, components=None):
        return False

    def is_noop(self):
        return False

class Comment(Instruction):
    pattern = re.compile(r'''
        \s*
        \/\/
        .*
        $
    ''', re.VERBOSE | re.MULTILINE)

class AssignmentInstruction(Instruction):
    pattern = re.compile(r'''
        \s*
        (?P<lval>\S+)
        \s* = \s*
        (?P<rval>\S.*)
        ;
    ''', re.VERBOSE)

    def __init__(self, text, lval, rval):
        Instruction.__init__(self, text)
        self.lval = lval.strip()
        self.rval = rval.strip()

    def writes(self, variable, components=None):
        return expression_is_register(self.lval, variable, components)

    def reads(self, variable, components=None):
        return register_in_expression(self.rval, variable, components)

    def is_noop(self):
        # For MGSV which has unoptimised shaders that do this a lot
        # print(repr(self.lval), repr(self.rval))
        return self.lval.strip() == self.rval.strip()

class MultiplyInstruction(AssignmentInstruction):
    pattern = re.compile(r'''
        \s*
        (?P<lval>\S+)
        \s* = \s*
        (?P<rval>
            (?P<arg1>\S+)
            \s* \* \s*
            (?P<arg2>\S+)
        )
        \s*
        ;
    ''', re.VERBOSE)

    def __init__(self, text, lval, rval, arg1, arg2):
        AssignmentInstruction.__init__(self, text, lval, rval)
        self.rargs = tuple(map(lambda x: expression_as_single_register(x) or x, (arg1, arg2)))

class AddInstruction(AssignmentInstruction):
    pattern = re.compile(r'''
        \s*
        (?P<lval>\S+)
        \s* = \s*
        (?P<rval>
            (?P<arg1>\S+)
            \s* \+ \s*
            (?P<arg2>\S+)
        )
        \s*
        ;
    ''', re.VERBOSE)

    def __init__(self, text, lval, rval, arg1, arg2):
        AssignmentInstruction.__init__(self, text, lval, rval)
        self.rargs = tuple(map(lambda x: expression_as_single_register(x) or x, (arg1, arg2)))

class ReciprocalInstruction(AssignmentInstruction):
    pattern = re.compile(r'''
        \s*
        (?P<lval>\S+)
        \s* = \s*
        (?P<rval>
            1 \s* \/ \s*
            (?P<arg>\S+)
        )
        \s*
        ;
    ''', re.VERBOSE)

    def __init__(self, text, lval, rval, arg):
        AssignmentInstruction.__init__(self, text, lval, rval)
        self.rargs = (expression_as_single_register(arg) or arg, )

class MADInstruction(AssignmentInstruction):
    pattern = re.compile(r'''
        \s*
        (?P<lval>\S+)
        \s* = \s*
        (?P<rval>
            (?P<arg1>\S+)
            \s* \* \s*
            (?P<arg2>\S+)
            \s* \+ \s*
            (?P<arg3>\S+)
        )
        \s*
        ;
    ''', re.VERBOSE)

    def __init__(self, text, lval, rval, arg1, arg2, arg3):
        AssignmentInstruction.__init__(self, text, lval, rval)
        self.rargs = tuple(map(lambda x: expression_as_single_register(x) or x, (arg1, arg2, arg3)))

class DotInstruction(AssignmentInstruction):
    pattern = re.compile(r'''
        \s*
        (?P<lval>\S+)
        \s* = \s*
        dot\(
            (?P<rval>
                (?P<arg1>\S+)
                \s* , \s*
                (?P<arg2>\S+)
            )
        \)
        \s*
        ;
    ''', re.VERBOSE)

    def __init__(self, text, lval, rval, arg1, arg2):
        AssignmentInstruction.__init__(self, text, lval, rval)
        self.rargs = tuple(map(lambda x: expression_as_single_register(x) or x, (arg1, arg2)))

class FlowControlStart(Instruction):
    pattern = re.compile(r'''
        \s*
        [^{};]+
        {
    ''', re.VERBOSE)

class FlowControlElse(Instruction):
    pattern = re.compile(r'''
        \s*
        } \s* else \s* {
    ''', re.VERBOSE)

class FlowControlEnd(Instruction):
    pattern = re.compile(r'''
        \s*
        }
    ''', re.VERBOSE)

specific_instructions = (
        MADInstruction,
        DotInstruction,
        MultiplyInstruction,
        AddInstruction,
        ReciprocalInstruction,
        AssignmentInstruction,
        FlowControlElse,
        FlowControlStart,
        FlowControlEnd,
)


# Tried to get rid of all the edge cases, probably still some left...
register_pattern = re.compile(r'''
    (?<![.])                            (?# Prevent matching structs like foo.bar.baz)
    (?P<negate>-)?
    \b                                  (?# Ensure we start on a world boundary)
    (?P<variable>[a-zA-Z][a-zA-Z0-9]*)
    (?:\[(?P<index>[0-9]+)\])?          (?# Match optional numeric index, not currently matching variable index)
    (?:[.](?P<components>[xyzw]+))?
    \b                                  (?# Ensure we end on a word boundary)
    (?![(.])                            (?# Prevent matching float2\(...\) or not matching components)
''', re.VERBOSE)

class Register(object):
    def __new__(cls, negate, variable, index, components):
        r = super(Register, cls).__new__(cls)
        r.negate = not not negate
        if index is not None:
            variable = '%s[%s]' % (variable, index)
        r.variable = variable
        r.components = components
        return r

    def __repr__(self):
        r = ''
        if self.negate:
            r += '-'
        r += self.variable
        if self.components is not None:
            r += '.' + self.components
        return r

    def __neg__(self):
        return Register(not self.negate, self.variable, None, self.components)

def find_regs_in_expression(expression):
    '''
    Returns a list of scalar/Register variables used in an expression. Does
    not return structs or literals, intended to be used to find register
    accesses.
    '''
    pos = 0
    regs = []
    while True:
        match = register_pattern.search(expression, pos)
        if match is None:
            break
        pos = match.end()
        register = Register(**match.groupdict())
        regs.append(register)
    return regs

def expression_as_single_register(expression):
    if isinstance(expression, Register):
        return expression
    match = register_pattern.search(expression)
    if match is None:
        return None
    if expression[:match.start()].strip() or expression[match.end():].strip():
        return None
    return Register(**match.groupdict())

def regs_overlap(register, variable, components):
    if register.variable != variable:
        return False

    if components is None:
        return True

    return set(components).intersection(set(register.components))

def expression_is_register(expression, variable, components):
    if components is None and expression == variable:
        return True

    match = register_pattern.match(expression)
    if match is None:
        return False

    register = Register(**match.groupdict())
    return regs_overlap(register, variable, components)

def register_in_expression(expression, variable, components=None):
    for reg in find_regs_in_expression(expression):
        if regs_overlap(reg, variable, components):
            return True
    return False

def str_reg_components(register, components):
    if not components:
        return register
    if isinstance(components, str):
        return register + '.%s' % components
    else:
        return register + '.%s' % component_set_to_string(components)

class Shader(object):
    '''
    Common code shared between HLSLShader in this file and ASMShader in
    asmtool.py
    '''

    shader_filename_pattern = re.compile(r'(?P<hash>[0-9a-f]{16})-(?P<shader_type>[vhdgpc]s)', re.IGNORECASE)

    def __init__(self, filename, args):
        self.filename = os.path.basename(filename)
        self.args = args
        self.autofixed = False
        self.vanity_inserted = False
        self.hash = None
        self.shader_type = None
        self.shader_model = None
        self._early_insert_pos = None
        self.inserted_stereo_params = False
        self.inserted_ini_params_decl = False
        self.inserted_ini_params = [False] * 8
        self.ini_settings = None
        self.ini_name = ''
        self.text = open(filename, 'r').read()
        self.get_info_from_filename()
        self.stereo_params_reg = None
        self.ini_params_reg = [None] * 8

    def get_info_from_filename(self):
        match = self.shader_filename_pattern.match(self.filename)
        if match is None:
            return None
        d = match.groupdict()
        self.hash = int(d['hash'], 16)
        self.shader_type = d['shader_type'].lower()

    def split_instructions(self, body_txt):
        self._body_txt = body_txt
        self.instructions = [];
        pos = 0
        while True:
            instr, pos = self.InstructionFactory(body_txt, pos)
            if instr is None:
                break
            debug_verbose(3, instr.__class__.__name__, instr.strip())

            if not instr.is_noop(): # No point adding noops, simplifies MGSV shaders
                self.instructions.append(instr)

            # Alternative noop handling - add line but comment it out:
            # if instr.is_noop(): # No point adding noops, simplifies MGSV shaders
            #     self.comment_out_instruction(-1, 'noop')
        return pos

    def scan_shader(self, reg, components=None, write=None, start=None, end=None, direction=1, stop=False, instr_type=None, stop_when_clobbered=False, stop_when_read=False):
        '''
        Based on the same function in shadertool
        '''
        assert(direction == 1 or direction == -1)
        assert(write is not None)

        if isinstance(reg, (list, tuple)):
            results = []
            for r in reg:
                results.extend(self.scan_shader(r, components=components,
                    write=write, start=start, end=end, direction=direction,
                    stop=stop, instr_type=instr_type,
                    stop_when_clobbered=stop_when_clobbered,
                    stop_when_read=stop_when_read))
            return results

        Match = collections.namedtuple('Match', ['line', 'instruction'])

        if instr_type and not isinstance(instr_type, (tuple, list)):
            instr_type = (instr_type, )

        if direction == 1:
            if start is None:
                start = 0
            if end is None:
                end = len(self.instructions)
        else:
            if start is None:
                start = len(self.instructions) - 1
            if end is None:
                end = -1

        if isinstance(reg, Register):
            if reg.components is not None:
                components = set(reg.components)
            reg = reg.variable

        debug_verbose(1, "Scanning shader %s from instruction %i to %i for %s %s%s..." % (
            {1: 'downwards', -1: 'upwards'}[direction],
            start, end - direction,
            {True: 'write to', False: 'read from'}[write],
            str_reg_components(reg, components),
            instr_type and ' (Searching for %s)' % ' or '.join([x.__name__ for x in instr_type]) or ''
            ))

        if isinstance(components, str):
            components = set(components)

        ret = []
        for i in range(start, end, direction):
            instr = self.instructions[i]
            debug_verbose(2, 'scanning %s' % instr.strip())

            if write:
                if instr.writes(reg, components):
                    if (not instr_type or isinstance(instr, instr_type)):
                        debug_verbose(1, 'Found write on instruction %s: %s' % (i, instr.strip()))
                        ret.append(Match(i, instr))
                        if stop:
                            return ret
                    elif stop_when_clobbered:
                        debug_verbose(1, 'Stopping search: Write from instruction %s clobbered register: %s' % (i, instr.strip()))
                        return ret

                if stop_when_read and instr.reads(reg, components):
                        debug_verbose(1, 'Stopping search: Unrelated read from instruction %s: %s' % (i, instr.strip()))
                        return ret
            else:
                if instr.reads(reg, components):
                    if (not instr_type or isinstance(instr, instr_type)):
                        debug_verbose(1, 'Found read on instruction %s: %s' % (i, instr.strip()))
                        ret.append(Match(i, instr))
                        if stop:
                            return ret
                    elif stop_when_read:
                        debug_verbose(1, 'Stopping search: Unrelated read from instruction %s: %s' % (i, instr.strip()))
                        return ret

                if stop_when_clobbered and instr.writes(reg, components):
                        debug_verbose(1, 'Stopping search: Write from instruction %s clobbered register: %s' % (i, instr.strip()))
                        return ret

        return ret

    def find_header(self, patterns):
        if not isinstance(patterns, (tuple, list)):
            patterns = (patterns, )

        for pattern in patterns:
            match = pattern.search(self.declarations_txt)
            if match is not None:
                return match

        raise KeyError()

    def find_unity_cb_entry(self, pattern, type):
        match = self.find_header(pattern)
        offset = int(match.group(type))

        pos = self.declarations_txt.rfind('ConstBuffer "', 0, match.start())
        if pos == -1:
            raise KeyError()
        match = unity_ConstBuffer_pattern.match(self.declarations_txt, pos)
        if match is None:
            raise KeyError()

        cb_name = match.group('name')
        cb_size = int(match.group('size'))

        pos = self.declarations_txt.find('BindCB "%s"' % cb_name, match.end())
        if pos == -1:
            raise KeyError()
        match = unity_BindCB_pattern.match(self.declarations_txt, pos)
        if match is None:
            raise KeyError()

        cb = int(match.group('cb'))

        self.adjust_cb_size(cb, cb_size)
        return cb, offset

    non_ws_pattern = re.compile('\S')
    def comment_out_instruction(self, line, additional=None):
        instr = str(self.instructions[line])
        match = self.non_ws_pattern.search(instr)
        instr = instr[:match.start()] + '// ' + instr[match.start():]
        if additional is not None:
            instr += ' // ' + additional
        self.instructions[line] = Comment(instr)

    def insert_vanity_comment(self, where, what):
        off = 0
        off += self.insert_instr(where + off)
        comments = vanity_comment(self.args, self, what)
        for comment in comments:
            off += self.insert_instr(where + off, comment = comment)
        #self.declarations_txt = ''.join([ '// %s\n' % comment for comment in comments ]) + self.declarations_txt
        if not self.vanity_inserted:
            self.declarations_txt = '// %s\n' % comments[1] + self.declarations_txt
            self.vanity_inserted = True
        return off

    def early_insert_vanity_comment(self, what):
        off = self.insert_vanity_comment(self.early_insert_pos, what)
        self.early_insert_pos += off
        return off

    def early_insert_instr(self, instruction=None, comment=None):
        self.early_insert_pos += self.insert_instr(self.early_insert_pos, instruction, comment)
        return 1

    def insert_multiple_lines(self, pos, lines):
        off = 0
        for line in map(str.rstrip, textwrap.dedent(lines).split('\n')):
            off += self.insert_instr(pos + off, line)
        return off

    def early_insert_multiple_lines(self, lines):
        off = 0
        for line in map(str.strip, lines.splitlines()):
            off += self.early_insert_instr(line)
        return off

    def set_ini_name(self, name):
            self.ini_name = name + '_'

    def add_shader_override_setting(self, setting, name=None):
        if self.ini_settings is None:
            self.ini_settings = []
        self.ini_settings.append(setting)

    def replace_reg_on_line(self, i, old, new, components=None):
        # NOTE: Replaces both lval and rval
        instr = self.instructions[i]
        if register_in_expression(str(instr), old, components):
            # FIXME: Use a regular expression replace to ensure the
            # replacement is on a word boundary:
            self.instructions[i] = self.InstructionFactory(str(instr).replace(old, new), 0)[0]
            return True
        return False

    def replace_rval_reg_on_line(self, i, old, new):
        instr = self.instructions[i]
        if register_in_expression(instr.rval, old):
            self.instructions[i] = instr.replace_rval_reg(old, new)

    def replace_reg(self, old, new, components = None, limit = None):
        count = 0
        for i in range(len(self.instructions)):
            count += self.replace_reg_on_line(i, old, new, components)
            if limit is not None and count >= limit:
                break
        return count

    def update_ini(self):
        '''
        Right now this just updates our internal data structures to note any
        changes we need to make to the ini file and we print these out before
        exiting. TODO: Actually update the ini file for real (still should notify
        the user).
        '''
        if self.ini_settings is None or self.hash is None:
            return

        section = 'ShaderOverride_%s%016x' % (self.ini_name, self.hash)
        d3dx_ini.setdefault(section, ['hash = %016x' % self.hash])
        d3dx_ini[section].extend(self.ini_settings)

class HLSLShader(Shader):
    main_start_pattern = re.compile(r'void main\(\s*')
    param_end_pattern = re.compile(r'\)\s*{')
    main_end_pattern = re.compile(r'^}$', re.MULTILINE)
    parameter_pattern = re.compile(r'''
        \s*
        (?P<output>out\s+)?
        (?P<modifiers>(?:(?:nointerpolation|linear|centroid|noperspective|sample)\s+)+)?
        (?P<type>(?:float|uint|int)[234]?)
        \s+
        (?P<variable>[a-zA-Z]\w*)
        \s*:\s*
        (?P<semantic>[a-zA-Z_]\w*)
        \s*
        ,?
    ''', re.VERBOSE)
    Parameter = collections.namedtuple('Parameter', ['output', 'modifiers', 'type', 'variable', 'semantic'])
    shader_model_pattern = re.compile(r'^(?://\s+Shader model )(?P<shader_type>[vhdgpc]s)_(?P<shader_model>[45]_[01])$', re.MULTILINE)

    class ParseError(Exception): pass
    class ParameterAlreadyExists(Exception): pass

    def __init__(self, filename):
        Shader.__init__(self, filename, args)

        self.main_match = self.main_start_pattern.search(self.text)
        self.param_end_match = self.param_end_pattern.search(self.text, self.main_match.end())
        main_end_match = self.main_end_pattern.search(self.text, self.param_end_match.end())

        self.declarations_txt = self.text[:self.main_match.start()]
        parameters_txt = self.text[self.main_match.end() : self.param_end_match.start()]
        body_txt = self.text[self.param_end_match.end() : main_end_match.start()]
        self.close_txt = self.text[main_end_match.start():main_end_match.end()]
        # Normalise ending whitespace as 3DMigoto adds an extra newline every
        # time the same shader is marked:
        self.tail_txt = self.text[main_end_match.end():].rstrip() + '\n'

        self.parse_parameters(parameters_txt)
        self.split_instructions(body_txt)

        self.guess_shader_type_and_model()
        debug_verbose(0, "Guessed shader model %s" % self.shader_model)

    def get_info_from_filename(self):
        Shader.get_info_from_filename(self)
        self.shader_model = '%s_5_0' % self.shader_type

    def guess_shader_type_and_model(self):
        '''
        This attempts to guess the shader model from comments inserted with
        dump_hlsl=2 or extract_unity_shaders.py
        '''
        # Try matching the model inserted by extract_unity_shaders:
        match = self.shader_model_pattern.search(self.declarations_txt)
        if match is None:
            # Try matching the model inserted by 3DMigoto with export_hlsl=2/3
            match = self.shader_model_pattern.search(self.tail_txt)
        if match is None:
            return
        d = match.groupdict()
        self.shader_type = d['shader_type']
        self.shader_model = '%s_%s' % (self.shader_type, d['shader_model'])

    def parse_parameters(self, parameters_txt):
        self.parameters = collections.OrderedDict()
        pos = 0
        while True:
            match = self.parameter_pattern.match(parameters_txt, pos)
            if match is None:
                if parameters_txt[pos:].strip():
                    # If we fuck this part up the shader will be damaged, so
                    # raise an exception now
                    raise self.ParseError(parameters_txt[pos:parameters_txt.find('\n', pos+1)].strip())
                break
            pos = match.end()
            groups = match.groupdict()
            groups['output'] = groups['output'] and True or False
            param = self.Parameter(**groups)
            self.parameters[(param.semantic, param.output)] = param

    def parameters_str(self):
        def parameter_str(param):
            out = ''
            if param.output:
                out = 'out '
            modifiers = param.modifiers or ''
            return '%s%s%s %s : %s' % (out, modifiers, param.type, param.variable, param.semantic)
        return ',\n  '.join(map(parameter_str, self.parameters.values()))

    def InstructionFactory(self, text, pos):
        match = Comment.pattern.match(text, pos)
        if match is not None:
            return Comment(match.group()), match.end()

        for specific_instruction in specific_instructions:
            match = specific_instruction.pattern.match(text, pos)
            if match is not None:
                return specific_instruction(match.group(), **match.groupdict()), match.end()

        match = Instruction.pattern.match(text, pos)
        if match is not None:
            return Instruction(match.group()), match.end()

        return None, pos

    def split_instructions(self, body_txt):
        pos = Shader.split_instructions(self, body_txt)
        self.close_txt = body_txt[pos:] + self.close_txt

    def lookup_semantic(self, semantic, output):
        return self.parameters[(semantic, output)]

    def lookup_output_position(self):
        try:
            return self.lookup_semantic('SV_Position0', True).variable
        except KeyError:
            try:
                return self.lookup_semantic('SV_POSITION0', True).variable
            except KeyError:
                return self.lookup_semantic('POSITION0', True).variable

    def add_parameter(self, output, modifiers, type, variable, semantic):
        # TODO: Insert parameter in appropriate spot (before certain SV
        # semantics, in order wrt other semantics of the same type)
        param = self.Parameter(output, modifiers, type, variable, semantic)
        if (semantic, output) in self.parameters:
            raise self.ParameterAlreadyExists((semantic, output))
        self.parameters[(semantic, output)] = param

    def find_var_component_from_row_major_matrix_multiply(self, cb):
        results = self.scan_shader(cb, write=False, instr_type=(MADInstruction, MultiplyInstruction, AddInstruction))
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

        if isinstance(instr, AddInstruction):
            var = '1'
        elif reg.components:
            assert(all([ x == reg.components[0] for x in reg.components[1:] ]))
            var = '%s.%s' % (reg.variable, reg.components[0])
        else:
            var = '%s.x' % reg.variable

        return var, line

    def hlsl_swizzle(self, mask, swizzle):
        return swizzle

    def adjust_cb_size(self, cb, size):
        search = '  float4 cb%d[' % cb
        pos = self.declarations_txt.find(search) + len(search)
        pos2 = self.declarations_txt.find(']', pos)
        if pos == -1 or pos2 == -1:
            return

        old_size = int(self.declarations_txt[pos:pos2])
        size = (size + 15) // 16
        if (old_size >= size):
            return
        debug_verbose(0, 'Resizing cb{0}[{1}] declaration to cb{0}[{2}]'.format(cb, old_size, size))
        self.declarations_txt = self.declarations_txt[:pos] + str(size) + self.declarations_txt[pos2:]

    def append_declaration(self, declaration):
        self.declarations_txt += '\n%s\n\n' % declaration.strip()

    def append_comment_to_line(self, line, comment):
        instr = str(self.instructions[line])
        instr += ' // ' + comment
        self.instructions[line] = Instruction(instr)

    def insert_instr(self, pos, instruction=None, comment=None):
        line = '\n'
        if instruction is not None:
            line += instruction
        if instruction is not None and comment is not None:
            line += ' '
        if comment is not None:
            line += '// ' + comment
        self.instructions.insert(pos, Instruction(line))
        return 1

    @property
    def early_insert_pos(self):
        if self._early_insert_pos is None:
            # Find first blank line
            # TODO: Should actually find first non definition line
            for i, instr in enumerate(self.instructions):
                if str(instr).startswith('\n\n'):
                    self._early_insert_pos = i
                    break
            else:
                self._early_insert_pos = 0
        return self._early_insert_pos

    @early_insert_pos.setter
    def early_insert_pos(self, value):
        self._early_insert_pos = value

    def insert_stereo_params(self):
        if self.inserted_stereo_params:
            return 0
        self.inserted_stereo_params = True
        off  = self.early_insert_instr()
        off += self.early_insert_instr('float4 stereo = StereoParams.Load(0);')
        off += self.early_insert_instr('float separation = stereo.x, convergence = stereo.y, eye = stereo.z;')
        self.stereo_params_reg = 'stereo'
        return off

    def insert_halo_fix_code(self, pos, temp_reg):
        return self.insert_instr(pos, 'if ({0}.w != 1.0) {{ {0}.x += separation * ({0}.w - convergence); }}'.format(temp_reg.variable))

    def __str__(self):
        s = self.declarations_txt
        s += self.main_match.group()
        s += self.parameters_str()
        s += self.param_end_match.group()
        for instr in self.instructions:
            s += str(instr)
        s += self.close_txt
        if not args.strip_tail:
            s += self.tail_txt
        return s

def do_ini_updates():
    if not d3dx_ini:
        return

    # TODO: Merge these into the ini file directly. Still print a message
    # for the user so they know what we've done.
    debug()
    debug()
    debug('!' * 79)
    debug('!' * 16 + ' Please add the following lines to the d3dx.ini ' + '!' * 15)
    debug('!' * 79)
    debug()
    for section in sorted(d3dx_ini):
        shadertool.write_ini('[%s]' % section)
        for line in d3dx_ini[section]:
            shadertool.write_ini(line)
        shadertool.write_ini()

def auto_fix_vertex_halo(shader):
    '''
    Based on shadertool --auto-fix-vertex-halo
    '''

    # 1. Find output position variable from declarations
    try:
        pos_out = shader.lookup_output_position()
    except KeyError:
        debug("Shader has no output position (tesselation?)")
        return

    # 2. Locate where in the shader the output position is set and note which
    #    temporary register was copied to it.
    results = shader.scan_shader(pos_out, components='xw', write=True)
    if not results:
        debug("Couldn't find write to output position register")
        return
    if len(results) > 1:
        # FUTURE: We may be able to handle certain cases of this
        debug_verbose(0, "Can't autofix a vertex shader writing to output position from multiple instructions")
        return
    (output_line, output_instr) = results[0]
    if not isinstance(output_instr, AssignmentInstruction):
        debug_verbose(-1, 'Output not using assignment: %s' % output_instr.strip())
        return
    out_reg = expression_as_single_register(output_instr.lval)
    temp_reg = expression_as_single_register(output_instr.rval)
    if temp_reg is None:
        debug_verbose(-1, 'Output not copied from a single register: %s' % output_instr.strip())
        return
    if not temp_reg.variable.startswith('r'):
        debug_verbose(-1, 'Output not moved from a temporary register: %s' % output_instr.strip())
        return
    if temp_reg.components and shader.hlsl_swizzle(out_reg.components, temp_reg.components) != out_reg.components:
        debug_verbose(-1, 'Temporary register has unexpected swizzle: %s' % output_instr.strip())
        return

    # 3. Scan upwards to find where the X or W components of the temporary
    #    register was last set.
    results = shader.scan_shader(temp_reg.variable, components='xw', write=True, start=output_line - 1, direction=-1, stop=True)
    if not results:
        debug('WARNING: Output set from undefined register!!!?!')
        return
    (temp_reg_line, temp_reg_instr) = results[0]


    # 4. Scan between the two lines identified in 2 and 3 for any reads of the
    #    temporary register. We only consider components that were originally
    #    output to avoid getting caught up on an unrelated variable:
    results = shader.scan_shader(temp_reg.variable, components=temp_reg.components, write=False, start=temp_reg_line + 1, end=output_line)
    if results:
        # 5. If temporary register was read between temporary register being set
        #    and moved to output, relocate the output to just before the first
        #    line that read from the temporary register
        relocate_to = results[0][0]

        # 6. Scan for any writes to other components of the temporary register
        #    that we may have just moved the output register past, and copy
        #    these to the output position at the original output location.
        #    Bug fix - Only consider components that were originally output
        #    (caused issue on Dreamfall Chapters Speedtree fadeout in fog).
        output_components = set('yzw')
        if temp_reg.components is not None:
            output_components = set(temp_reg.components).intersection(output_components)

        results = shader.scan_shader(temp_reg.variable, components=output_components, write=True, start=relocate_to + 1, end=output_line)
        off = 0
        if results:
            components = [ tuple(expression_as_single_register(instr.lval).components) for (_, instr) in results ]
            components = component_set_to_string(set(itertools.chain(*components)).intersection(output_components))

            # This comment from shadertool.py:
            #   " Only apply components to destination (as mask) to avoid bugs like this one: "mov o6.yz, r1.yz" "
            # does not apply here as HLSL does not use a mask in the same way.
            # Instead we apply the mask to both input & output:
            instr = '%s.%s = %s.%s;' % (pos_out, components, temp_reg.variable, components)
            debug_verbose(-1, "Line %i: Inserting '%s'" % (output_line + 1, instr))
            off = shader.insert_instr(output_line + 1, instr, 'Inserted by %s' % tool_name)

        # Actually do the relocation from 5 (FIXME: Move this up, being careful
        # of position offsets):
        shader.comment_out_instruction(output_line, 'Relocated from here with %s' % tool_name)
        debug_verbose(-1, "Line %i: %s" % (output_line, shader.instructions[output_line].strip()))
        shader.insert_instr(output_line + 1 + off)
        shader.insert_instr(output_line)
        debug_verbose(-1, "Line %i: Relocating '%s' to here" % (relocate_to, output_instr.strip()))
        relocate_to += shader.insert_instr(relocate_to)
        relocate_to += shader.insert_instr(relocate_to, output_instr.strip(), 'Relocated to here with %s' % tool_name)
        output_line = relocate_to - 1
    else:
        # 7. No reads above, scan downwards until temporary register X
        #    component is next set:
        results = shader.scan_shader(temp_reg.variable, components='x', write=True, start=output_line, stop=True)
        scan_until = len(shader.instructions)
        if results:
            scan_until = results[0].line

        # 8. Scan between the two lines identified by 2 and 7 for any reads of
        #    the temporary register:
        results = shader.scan_shader(temp_reg.variable, write=False, start=output_line + 1, end=scan_until, stop=True)
        if not results:
            debug_verbose(0, 'No other reads of temporary variable found, nothing to fix')
            return

    # 9. Insert stereo conversion after new location of move to output position.
    # FIXME: Reuse a previously inserted stereo declaration
    pos = output_line + 1

    debug_verbose(-1, 'Line %i: Applying stereo correction formula to %s' % (pos, temp_reg.variable))
    pos += shader.insert_vanity_comment(pos, "Automatic vertex shader halo fix inserted with")

    pos += shader.insert_stereo_params()
    pos += shader.insert_halo_fix_code(pos, temp_reg)
    pos += shader.insert_instr(pos)

    shader.autofixed = True

class cb_offset(str):
    def __new__(cls, cb, offset):
        return str.__new__(cls, 'cb%d[%d]' % (cb, offset//16))
    def __init__(self, cb, offset):
        self.cb = cb
        self.offset = offset

def cb_matrix(cb, offset):
    return [ cb_offset(cb, offset + i) for i in range(0, 64, 16) ]

def hlsl_matrix(a, b, c, d):
    return 'matrix(%s, %s, %s, %s)' % (a, b, c, d)

def fix_unity_lighting_ps(shader):
    try:
        _CameraToWorld = cb_matrix(*shader.find_unity_cb_entry(shadertool.unity_CameraToWorld, 'matrix'))
    except KeyError:
        debug_verbose(0, 'Shader does not use _CameraToWorld, or is missing headers (my other scripts can extract these)')
        return

    try:
        _WorldSpaceCameraPos = cb_offset(*shader.find_unity_cb_entry(shadertool.unity_WorldSpaceCameraPos, 'constant'))
    except KeyError:
        debug_verbose(0, 'Shader does not use _WorldSpaceCameraPos - skipping environment/specular adjustment')
        _WorldSpaceCameraPos = None

    try:
        _ZBufferParams_cb, _ZBufferParams_offset = shader.find_unity_cb_entry(shadertool.unity_ZBufferParams, 'constant')
        _ZBufferParams = cb_offset(_ZBufferParams_cb, _ZBufferParams_offset)
    except KeyError:
        debug_verbose(0, 'Shader does not use _ZBufferParams, or is missing headers (my other scripts can extract these)')
        return

    # XXX: Directional lighting shaders seem to have a bogus _ZBufferParams!
    try:
        match = shader.find_header(shadertool.unity_headers_attached)
    except KeyError:
        debug('Skipping possible depth buffer source - shader does not have Unity headers attached so unable to check what kind of lighting shader it is')
        has_unity_headers = False
    else:
        has_unity_headers = True
        try:
            match = shader.find_header(shadertool.unity_shader_directional_lighting)
        except KeyError:
            try:
                match = shader.find_header(shadertool.unity_CameraDepthTexture)
            except KeyError:
                debug_verbose(0, 'Shader does not use _CameraDepthTexture')
                return
            _CameraDepthTexture = 't' + match.group('texture')
        else:
            _CameraDepthTexture = None

    debug_verbose(0, '_CameraToWorld in %s, _ZBufferParams in %s' % (hlsl_matrix(*_CameraToWorld), _ZBufferParams))

    # Find _CameraToWorld usage - adjustment must be above this point, and this
    # gives us the register with X that needs to be adjusted:
    x_var, _CameraToWorld_line = shader.find_var_component_from_row_major_matrix_multiply(_CameraToWorld[0])

    # Since the compiler often places y first, for clarity use it's position to insert the correction:
    _, line_y = shader.find_var_component_from_row_major_matrix_multiply(_CameraToWorld[1])
    _CameraToWorld_line = min(_CameraToWorld_line, line_y)

    # And once more to find register with Z to use as depth:
    depth, line_z = shader.find_var_component_from_row_major_matrix_multiply(_CameraToWorld[2])
    shader.append_comment_to_line(line_z, 'depth in %s' % depth)
    depth_reg = expression_as_single_register(depth)

    # And to find the end for the fallback world space adjustment:
    _, _CameraToWorld_end = shader.find_var_component_from_row_major_matrix_multiply(_CameraToWorld[3])
    _CameraToWorld_end = max(_CameraToWorld_end, line_z, line_y, _CameraToWorld_line)
    world_reg = expression_as_single_register(shader.instructions[_CameraToWorld_end].lval)


    # Find _ZBufferParams usage to find where depth is sampled (could use
    # _CameraDepthTexture, but that takes an extra step and more can go wrong)
    results = shader.scan_shader(_ZBufferParams, write=False, end=_CameraToWorld_line)
    if len(results) != 1:
        # XXX: In shadertool.py scan_shader returns the two reads on the one
        # instruction, currently we only return one per instruction
        debug_verbose(0, '_ZBufferParams read %i times (only exactly 1 reads currently supported)' % len(results))
        return
    (line, instr) = results[0]
    reg = expression_as_single_register(instr.lval)

    # We're expecting a reciprocal calculation as part of the Z buffer -> world
    # Z scaling:
    results = shader.scan_shader(reg.variable, components=reg.components, instr_type=ReciprocalInstruction,
            write=False, start=line+1, end=_CameraToWorld_line, stop=True)
    if not results:
        debug_verbose(0, 'Could not find expected reciprocal instruction')
        return
    (line, instr) = results[0]
    reg = expression_as_single_register(instr.lval)

    # Find where the reciprocal is next used:
    results = shader.scan_shader(reg.variable, components=reg.components, write=False,
            start=line+1, end=_CameraToWorld_line, stop=True)
    if not results:
        debug_verbose(0, 'Could not find expected instruction')
        return
    (line, instr) = results[0]
    reg = expression_as_single_register(instr.lval)

    # We used to trace the function forwards more here, but Dreamfall Chapters
    # got complicated after the Unity 5 update. Now we find the depth from the
    # matrix multiply instead, which hopefully should be more robust.

    # If we ever need the old procedure, it's in the git history of shadertool.py.

    # Find where the depth was set and store it in a variable:
    results = shader.scan_shader(depth_reg.variable, components=depth_reg.components, write=True,
            start=line_z, end=line-1, stop=True, direction=-1)
    if not results:
        debug_verbose(0, 'Could not find where depth was set')
        return
    (depth_line, _) = results[0]

    # TODO: Add comment 'New input from vertex shader with unity_CameraInvProjection[0].x'
    shader.add_parameter(False, None, 'float', 'fov', args.fix_unity_lighting_ps)

    shader.append_declaration(UnityPerDraw)
    shader.append_declaration(include_matrix_hlsl)

    offset = shader.insert_stereo_params()

    # Apply a stereo correction to the world space camera position - this
    # pushes environment reflections, specular highlights, etc to the correct
    # depth in Unity 5. Skip adjustment for Unity 4 style shaders that don't
    # use the world space camera position:
    if _WorldSpaceCameraPos is not None:
        shader.replace_reg(_WorldSpaceCameraPos, '_WorldSpaceCameraPos', 'xyz')
        offset += shader.early_insert_vanity_comment("Unity reflection/specular fix inserted with")
        offset += shader.early_insert_instr('matrix _CameraToWorld = %s;' % hlsl_matrix(*_CameraToWorld))
        offset += shader.early_insert_instr('float4 _WorldSpaceCameraPos = %s;' % _WorldSpaceCameraPos)
        offset += shader.early_insert_instr('if (fov) {')
        offset += shader.early_insert_instr('  _WorldSpaceCameraPos.xyz -= mul(float4(-separation * convergence * fov, 0, 0, 0), _CameraToWorld).xyz;')
        offset += shader.early_insert_instr('} else {')
        offset += shader.early_insert_instr('  float4 clip_space_adj = float4(-separation * convergence, 0, 0, 0);')
        offset += shader.early_insert_instr('  float4 local_space_adj = mul(inverse(glstate_matrix_mvp), clip_space_adj);')
        offset += shader.early_insert_instr('  float4 world_space_adj = mul(_Object2World, local_space_adj);')
        offset += shader.early_insert_instr('  _WorldSpaceCameraPos.xyz -= world_space_adj.xyz;')
        offset += shader.early_insert_instr('}')

    offset += shader.insert_instr(depth_line + offset + 1, 'float depth = %s;' % depth);

    pos = _CameraToWorld_line + offset
    debug_verbose(-1, 'Line %i: Applying Unity pixel shader light/shadow fix. depth in %s, x in %s' % (pos, depth, x_var))
    pos += shader.insert_vanity_comment(pos, "Unity light/shadow fix (pixel shader stage) inserted with")
    pos += shader.insert_instr(pos, 'if (fov) {')
    pos += shader.insert_instr(pos, '  %s -= separation * (depth - convergence) * fov;' % (x_var))
    pos += shader.insert_instr(pos, '}')
    pos += shader.insert_instr(pos)

    pos = pos - _CameraToWorld_line + _CameraToWorld_end + 1
    pos += shader.insert_instr(pos)
    pos += shader.insert_instr(pos, '// Fallback adjustment if the FOV was not passed from the VS:')
    pos += shader.insert_instr(pos, 'if (!fov) {')
    pos += shader.insert_instr(pos, '  float4 clip_space_adj = float4(separation * (depth - convergence), 0, 0, 0);')
    pos += shader.insert_instr(pos, '  float4 local_space_adj = mul(inverse(glstate_matrix_mvp), clip_space_adj);')
    pos += shader.insert_instr(pos, '  float4 world_space_adj = mul(_Object2World, local_space_adj);')
    pos += shader.insert_instr(pos, '  %s.%s -= world_space_adj.xyz;' % (world_reg.variable, world_reg.components[:3]))
    pos += shader.insert_instr(pos, '}')
    pos += shader.insert_instr(pos)

    shader.add_shader_override_setting('%s-cb11 = Resource_UnityPerDraw' % (shader.shader_type));

    if has_unity_headers and _CameraDepthTexture is not None:
        shader.add_shader_override_setting('Resource_CameraDepthTexture = ps-%s' % _CameraDepthTexture);
        shader.add_shader_override_setting('Resource_UnityPerCamera = ps-cb%d' % _ZBufferParams_cb);

    shader.autofixed = True

def possibly_copy_unity_world_matrices(shader):
    # We might possibly use this shader as a source of the MVP and
    # _Object2World matrices, but only if it is rendering from the POV of the
    # camera. Blacklist shadow casters which are rendered from the POV of a
    # light.
    #
    # No longer blacklisting IGNOREPROJECTOR shaders - I was never sure what
    # that tag signified, but it's clear that they do/can have valid matrices,
    # and some scenes (e.g. falling Dreamer in Dreamfall chapter 1) only have
    # the matrices we want in these shaders.
    #
    # This blacklisting may not be necessary - I doubt that any shadow casters
    # will have used _WorldSpaceCameraPos and we won't have got this far.
    try:
        match = shader.find_header(shadertool.unity_headers_attached)
    except KeyError:
        debug('Skipping possible matrix source - shader does not have Unity headers attached so unable to check if it is a SHADOWCASTER')
        # tree.ini.append((None, None, 'Skipping possible matrix source - shader does not have Unity headers attached so unable to check if it is a SHADOWCASTER'))
        return False

    try:
        match = shader.find_header(shadertool.unity_tag_shadow_caster)
    except KeyError:
        pass
    else:
        debug('Skipping possible matrix source - shader is a SHADOWCASTER')
        # tree.ini.append((None, None, 'Skipping possible matrix source - shader is a SHADOWCASTER'))
        return False

    try:
        unity_glstate_matrix_mvp_cb, unity_glstate_matrix_mvp_offset = \
                shader.find_unity_cb_entry(shadertool.unity_glstate_matrix_mvp_pattern, 'matrix')
        assert(unity_glstate_matrix_mvp_offset == 0) # If this fails I need to handle the variations somehow
        _Object2World0_cb, _Object2World0_offset = \
                shader.find_unity_cb_entry(shadertool.unity_Object2World, 'matrix')
        assert(_Object2World0_offset == 192) # If this fails I need to handle the variations somehow
        assert(unity_glstate_matrix_mvp_cb == _Object2World0_cb) # If this fails I need to handle the variations somehow
        shader.add_shader_override_setting('Resource_UnityPerDraw = %s-cb%d' % (shader.shader_type, unity_glstate_matrix_mvp_cb));
        return True
    except KeyError:
        return False

def fix_unity_reflection(shader):
    try:
        _WorldSpaceCameraPos = cb_offset(*shader.find_unity_cb_entry(shadertool.unity_WorldSpaceCameraPos, 'constant'))
    except KeyError:
        debug_verbose(0, 'Shader does not use _WorldSpaceCameraPos')
        return

    shader.append_declaration(UnityPerDraw)
    shader.append_declaration(include_matrix_hlsl)

    shader.insert_stereo_params()

    # Apply a stereo correction to the world space camera position - this
    # pushes environment reflections, specular highlights, etc to the correct
    # depth
    shader.replace_reg(_WorldSpaceCameraPos, '_WorldSpaceCameraPos', 'xyz')
    shader.early_insert_vanity_comment("Unity reflection/specular fix inserted with")
    shader.early_insert_instr('float4 _WorldSpaceCameraPos = %s;' % _WorldSpaceCameraPos)
    shader.early_insert_instr('float4 clip_space_adj = float4(-separation * convergence, 0, 0, 0);')
    shader.early_insert_instr('float4 local_space_adj = mul(inverse(glstate_matrix_mvp), clip_space_adj);')
    shader.early_insert_instr('float4 world_space_adj = mul(_Object2World, local_space_adj);')
    shader.early_insert_instr('_WorldSpaceCameraPos.xyz -= world_space_adj.xyz;')

    possibly_copy_unity_world_matrices(shader)

    # Do this last so we can use our own resources if we are the first in the frame:
    shader.add_shader_override_setting('%s-cb11 = Resource_UnityPerDraw' % (shader.shader_type));

    shader.autofixed = True

def fix_unity_frustum_world(shader):
    try:
        _FrustumCornersWS = cb_matrix(*shader.find_unity_cb_entry(shadertool.unity_FrustumCornersWS, 'matrix'))
    except KeyError:
        debug_verbose(0, 'Shader does not use _FrustumCornersWS, or is missing headers (my other scripts can extract these)')
        return

    shader.append_declaration(UnityPerDraw)
    shader.append_declaration(UnityPerCamera)
    shader.append_declaration(include_matrix_hlsl)

    shader.insert_stereo_params()

    for i in range(3):
        shader.replace_reg(_FrustumCornersWS[i], '_FrustumCornersWS[%d]' % i, 'xyzw')

    # Apply a stereo correction to the world space frustum corners - this
    # fixes the glow around the sun in The Forest (shaders called Sunshine
    # PostProcess Scatter)
    shader.early_insert_vanity_comment("Unity _FrustumCornersWS fix inserted with")
    shader.early_insert_instr('float far = 1 / (_ZBufferParams.z + _ZBufferParams.w);')
    shader.early_insert_instr('float4 clip_space_adj = float4(separation * (far - convergence), 0, 0, 0);')
    shader.early_insert_instr('float4 local_space_adj = mul(inverse(glstate_matrix_mvp), clip_space_adj);')
    shader.early_insert_instr('float4 world_space_adj = mul(_Object2World, local_space_adj);')
    shader.early_insert_instr('// GOTCHA: _FrustumCornersWS is TRANSPOSED vs DX9!')
    shader.early_insert_instr('float4x4 _FrustumCornersWS = %s;' % hlsl_matrix(*_FrustumCornersWS))
    shader.early_insert_instr('_FrustumCornersWS[0].xyzw -= world_space_adj.x;')
    shader.early_insert_instr('_FrustumCornersWS[1].xyzw -= world_space_adj.y;')
    shader.early_insert_instr('_FrustumCornersWS[2].xyzw -= world_space_adj.z;')

    shader.add_shader_override_setting('%s-cb11 = Resource_UnityPerDraw' % (shader.shader_type));
    shader.add_shader_override_setting('%s-cb13 = Resource_UnityPerCamera' % (shader.shader_type));

    shader.autofixed = True

def fix_unity_sun_shafts(shader):
    try:
        _SunPosition = cb_offset(*shader.find_unity_cb_entry(shadertool.unity_SunPosition, 'constant'))
    except KeyError:
        debug_verbose(0, 'Shader does not use _SunPosition, or is missing headers (my other scripts can extract these)')
        return

    shader.insert_stereo_params()

    shader.early_insert_vanity_comment("Unity sun position fix inserted with")
    shader.replace_reg(_SunPosition, '_SunPosition', 'xy')
    shader.early_insert_instr('float4 _SunPosition = %s;' % _SunPosition)
    shader.early_insert_instr('_SunPosition.x += separation / 2;')

    shader.autofixed = True

def find_game_dir(file):
    src_dir = os.path.dirname(os.path.realpath(os.path.join(os.curdir, file)))
    if os.path.basename(src_dir).lower() in ('shaderfixes', 'shadercache'):
        return os.path.realpath(os.path.join(src_dir, '..'))
    raise ValueError('Unable to find game directory')

# FIXME: Unchanged from shadertool, but copied here as the functions it calls
# are changed. Should be able to solve this duplicated code with some refactoring
def install_shader_to_git(shader, file, args):
    game_dir = find_game_dir(file)

    # Filter out common subdirectory names:
    blacklisted_names = ('win32', 'win64', 'binaries', 'bin', 'win_x86', 'win_x64')
    while os.path.basename(game_dir).lower() in blacklisted_names:
        game_dir = os.path.realpath(os.path.join(game_dir, '..'))

    dest_dir = game_git_dir(game_dir)

    return install_shader_to(shader, file, args, dest_dir, True)

def validate_shader_compiles(filename, shader_model):
    import subprocess

    if shader_model is None:
        debug_verbose('Could not determine shader model - will not validate')
        return

    cwd = os.getcwd()
    os.chdir(os.path.dirname(os.path.realpath(filename)))
    try:
        # Don't disable optimisations since doing so suppresses certain errors
        # (e.g. 'Output variable o0 contains a system-interpreted value
        # (SV_Position0) which must be written in every execution path of the
        # shader.'). We want the errors to be consistent with 3DMigoto's
        # compilation step to catch all the same failures it does.
        fxc = subprocess.Popen([os.path.expanduser(args.fxc),
            '/T', shader_model, '/I', '..', os.path.basename(filename)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = fxc.communicate()
    except OSError as e:
        os.chdir(cwd)
        os.remove(filename)
        raise
    os.chdir(cwd)

    err_type = None
    if err:
        debug(err.decode('cp1252'))
        err_type = 'WARNINGS'
    if fxc.returncode != 0:
        failed_filename = filename + '~failed'
        os.rename(filename, failed_filename)
        filename = failed_filename
        err_type = 'ERRORS'

    if err:
        with open(filename, 'a') as f:
            print('\n/****************************** COMPILE %s ******************************' % err_type, file=f)
            print(err.decode('ascii').replace('\r', ''), end='', file=f)
            print('****************************** COMPILE %s ******************************/' % err_type, file=f)

def alt_filenames(filename):
    ''' Returns iterator over alternate filenames for a shader - HLSL, ASM, and ~failed '''
    yield (filename, True)
    yield (filename + '~bad', False)
    f = filename.lower()
    if f.endswith('_replace.txt'):
        yield (filename + '~failed', True)
        f =  filename.rsplit('_', 1)[0] + '.txt'
        yield (f, True)
        yield (f + '~bad', False)
    elif f.endswith('.txt'):
        f = os.path.splitext(filename)[0] + '_replace.txt'
        yield (f, True)
        yield (f + '~bad', False)
    else:
        debug('Unable to determine alternate filename of %s' % filename)

def install_shader_to(shader, file, args, base_dir, show_full_path=False):
    try:
        os.mkdir(base_dir)
    except OSError:
        pass

    shader_dir = os.path.join(base_dir, 'ShaderFixes')
    try:
        os.mkdir(shader_dir)
    except OSError:
        pass

    dest_name = os.path.basename(file)
    for (check_name, force_allowed) in alt_filenames(dest_name):
        check_dest = os.path.join(shader_dir, check_name)
        if os.path.exists(check_dest):
            if not force_allowed:
                debug_verbose(0, 'Skipping %s - marked bad' % dest_name)
                return False
            if args.force:
                if dest_name != check_name:
                    debug_verbose(0, 'Removing shader with alternate filename %s' % check_dest)
                    os.remove(check_dest)
            elif dest_name == check_name:
                debug_verbose(0, 'Skipping %s - already installed' % dest_name)
                return False
            else:
                debug_verbose(0, 'Skipping %s - shader with alternate filename %s already installed' % (dest_name, check_name))
                return False

    dest = os.path.join(shader_dir, dest_name)

    if show_full_path:
        debug_verbose(0, 'Installing to %s...' % dest)
    else:
        debug_verbose(0, 'Installing to %s...' % os.path.relpath(dest, os.curdir))
    print(shader, end='', file=open(dest, 'w'))

    if hasattr(args, 'validate') and args.validate and args.fxc:
        validate_shader_compiles(dest, shader.shader_model)

    return True # Returning success will allow ini updates

def install_shader(shader, file, args):
    src_dir = os.path.dirname(os.path.join(os.path.realpath(os.curdir), file))
    if os.path.basename(src_dir).lower() != 'shadercache':
        raise Exception("Not installing %s - not in a ShaderCache directory" % file)
    gamedir = os.path.realpath(os.path.join(src_dir, '..'))

    return install_shader_to(shader, file, args, gamedir)

def parse_args():
    global args

    parser = argparse.ArgumentParser(description = 'nVidia 3D Vision Shaderhacker Tool')
    parser.add_argument('files', nargs='+',
            help='List of HLSL files to process')

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

    parser.add_argument('--fxc',
            help='Path to fxc to validate that the shader compiles')
    parser.add_argument('--no-validate', dest='validate', action='store_false',
            help='Do not validate that the shader will compile')

    parser.add_argument('--strip-tail', '-s', action='store_true',
            help='Strip everything after the main function in the shader')

    parser.add_argument('--auto-fix-vertex-halo', action='store_true',
            help="Attempt to automatically fix a vertex shader for common halo type issues")
    parser.add_argument('--fix-unity-lighting-ps', nargs='?', const='TEXCOORD3',
            help="Apply a correction to Unity lighting pixel shaders. NOTE: This is only one part of the Unity lighting fix - you also need the vertex shaders & d3dx.ini from my template!")
    parser.add_argument('--fix-unity-reflection', action='store_true',
            help="Correct the Unity camera position to fix certain cases of specular highlights, reflections and some fake transparent windows. Requires a valid MVP and _Object2World matrices copied from elsewhere")
    parser.add_argument('--fix-unity-frustum-world', action='store_true',
            help="Applies a world-space correction to _FrustumCornersWS. Requires a valid MVP and _Object2World matrices copied from elsewhere")
    parser.add_argument('--fix-unity-sun-shafts', action='store_true',
            help="Fix Unity SunShaftsComposite")
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

    if (args.install or args.install_to) and not args.fxc and args.validate:
        parser.error("Must specify either --fxc or --no-validate when installing a shader");

    shadertool.verbosity = args.verbose - args.quiet

def main():
    parse_args()
    shadertool.expand_wildcards(args)
    for file in args.files:
        debug_verbose(-2, 'parsing %s...' % file)
        shader = HLSLShader(file)

        try:
            if args.auto_fix_vertex_halo:
                auto_fix_vertex_halo(shader)
            if args.fix_unity_lighting_ps:
                fix_unity_lighting_ps(shader)
            if args.fix_unity_reflection:
                fix_unity_reflection(shader)
            if args.fix_unity_frustum_world:
                fix_unity_frustum_world(shader)
            if args.fix_unity_sun_shafts:
                fix_unity_sun_shafts(shader)
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
                if install_shader(shader, file, args):
                    shader.update_ini()
                    pass
            if args.install_to:
                if install_shader_to(shader, file, args, os.path.expanduser(args.install_to), True):
                    shader.update_ini()
                    pass
            if args.to_git:
                a = copy.copy(args)
                a.force = True
                if install_shader_to_git(shader, file, a):
                    shader.update_ini()
    show_collected_errors()
    do_ini_updates()

if __name__ == '__main__':
    main()

# vi: et ts=4:sw=4
