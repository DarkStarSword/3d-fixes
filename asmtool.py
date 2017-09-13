#!/usr/bin/env python3

# Port of shadertool to DX11. I thought long and hard about adapting shadertool
# to work with both, but eventually decided to make a clean start since there
# are quite a few differences between DX9 and DX11 shaders, and this way I
# could take a clean slate with some of the lessons learned working on
# shadertool and hlsltool and have cleaner code from the beginning. Some code
# from shadertool and hlsltool is still reused. Like hlsltool this is intended
# to use an approach based purely on pattern matching instead of the parser in
# shadertool, which may not be as powerful, but should be simpler.

import sys, os, re, collections, argparse, itertools, copy, textwrap

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
            (?: \s+ \[(?P<unused>unused)\] )?
            \s* $
        '''.format(type, name), re.VERBOSE | re.MULTILINE)
        cbuffer_entry_pattern_cache[(type, name)] = pattern
        return pattern

struct_entry_pattern_cache = {}
def struct_entry_pattern(struct, type, entry):
    try:
        return struct_entry_pattern_cache[(struct, type, entry)]
    except KeyError:
        pattern = re.compile(r'''
            // \s Resource \s bind \s info \s for \s (?P<bind_name>\S+) \s* \n
            // \s* {{ \s* \n
            //   \s* \n
            //   \s* struct \s+ {0} \s* \n
            //   \s* {{ \s* \n
                   [^}}]*
            //     \s* {1} \s+ {2}; \s* // \s* Offset: \s+ (?P<offset>\d+) \s* \n
                   [^}}]*
            //   \s* }} \s+ [$]Element; \s* // \s* Offset: \s+ 0 \s+ Size: \s+ (?P<size>\d+) \s* \n
            //   \s* \n
            // \s* }}
        '''.format(struct, type, entry), re.VERBOSE | re.MULTILINE)
        struct_entry_pattern_cache[(struct, type, entry)] = pattern
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

resource_bindings_pattern = re.compile(r'// Resource Bindings:')

def cbuffer_bind_pattern(cb_name):
    return resource_bind_pattern(cb_name, 'cbuffer', 'NA', 'NA')
def struct_bind_pattern(cb_name):
    return resource_bind_pattern(cb_name, 'texture', 'struct', 'r/o')

cbuffer_pattern = re.compile(r'// cbuffer (?P<name>.+)\n// {$', re.MULTILINE)
struct_pattern = re.compile(r'// Resource bind info for (?P<name>.+)\n// {$', re.MULTILINE)

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
        \s* , \s*
        (?P<rval>\S.*)
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE)

    def __init__(self, text, instruction, lval, rval):
        Instruction.__init__(self, text)
        self.instruction = instruction
        self.lval = hlsltool.expression_as_single_register(lval)
        self.rval = rval.strip()

    def writes(self, variable, components=None):
        return hlsltool.regs_overlap(self.lval, variable, components)

    def reads(self, variable, components=None):
        return hlsltool.register_in_expression(self.rval, variable, components)

    def is_noop(self):
        return False

    def replace_rval_reg(self, old, new):
        indent = self.text[:self.text.find(self.instruction)]
        text = '{}{} {}, {}'.format(indent, self.instruction, self.lval, self.rval.replace(old, new))
        match = self.__class__.pattern.match(text)
        return self.__class__(match.group(), **match.groupdict())

class MovInstruction(AssignmentInstruction):
    pattern = re.compile(r'''
        \s*
        (?P<instruction>mov)
        \s+
        (?P<lval>\S+)
        \s* , \s*
        (?P<rval>\S+)
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE)

    def __init__(self, text, instruction, lval, rval):
        AssignmentInstruction.__init__(self, text, instruction, lval, rval) # rval is text for consistency
        self.rarg = hlsltool.expression_as_single_register(rval) or rval # rarg is Register if possible

class ResourceLoadInstruction(AssignmentInstruction):
    pattern = re.compile(r'''
        \s*
        (?P<instruction>[a-zA-Z_]+
            \s*
            (?:
                \(
                    [^)]+
                \)
            )+
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

class SampleIndexableInstruction(ResourceLoadInstruction):
    pattern = re.compile(r'''
        \s*
        (?P<instruction>sample_indexable
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
        )
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE)

    def __init__(self, text, instruction, lval, rval, arg1, arg2, arg3):
        AssignmentInstruction.__init__(self, text, instruction, lval, rval)
        self.rargs = tuple(map(lambda x: hlsltool.expression_as_single_register(x) or x, (arg1, arg2, arg3)))

class LoadStructuredInstruction(ResourceLoadInstruction):
    pattern = re.compile(r'''
        \s*
        (?P<instruction>ld_structured_indexable
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
        )
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE)

    def __init__(self, text, instruction, lval, rval, arg1, arg2, arg3):
        AssignmentInstruction.__init__(self, text, instruction, lval, rval)
        self.rargs = tuple(map(lambda x: hlsltool.expression_as_single_register(x) or x, (arg1, arg2, arg3)))

class TwoArgAssignmentInstruction(AssignmentInstruction):
    @staticmethod
    def mkpattern(instruction):
        return re.compile(r'''
            \s*
            (?P<instruction>{})
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
        '''.format(instruction), re.MULTILINE | re.VERBOSE)

    def __init__(self, text, instruction, lval, rval, arg1, arg2):
        AssignmentInstruction.__init__(self, text, instruction, lval, rval)
        self.rargs = tuple(map(lambda x: hlsltool.expression_as_single_register(x) or x, (arg1, arg2)))

class DP2Instruction(TwoArgAssignmentInstruction):
    pattern = TwoArgAssignmentInstruction.mkpattern('dp2')

class DP3Instruction(TwoArgAssignmentInstruction):
    pattern = TwoArgAssignmentInstruction.mkpattern('dp3')

class DP4Instruction(TwoArgAssignmentInstruction):
    pattern = TwoArgAssignmentInstruction.mkpattern('dp4')

class AddInstruction(TwoArgAssignmentInstruction, hlsltool.AddInstruction):
    pattern = TwoArgAssignmentInstruction.mkpattern('add')

class MulInstruction(TwoArgAssignmentInstruction, hlsltool.MultiplyInstruction):
    pattern = TwoArgAssignmentInstruction.mkpattern('mul')

class DivInstruction(TwoArgAssignmentInstruction):
    pattern = TwoArgAssignmentInstruction.mkpattern('div')

class MinInstruction(TwoArgAssignmentInstruction):
    pattern = TwoArgAssignmentInstruction.mkpattern('min')

class MaxInstruction(TwoArgAssignmentInstruction):
    pattern = TwoArgAssignmentInstruction.mkpattern('max')

class ReciprocalInstruction(TwoArgAssignmentInstruction, hlsltool.ReciprocalInstruction):
    pattern = re.compile(r'''
        \s*
        (?P<instruction>div)
        \s+
        (?P<lval>\S+)
        \s* , \s*
        (?P<rval>
            (?P<arg1>l\(1.0+, \s* 1.0+, \s* 1.0+, \s* 1.0+\))
            \s* , \s*
            (?P<arg2>\S+)
        )
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE)

class MADInstruction(AssignmentInstruction, hlsltool.MADInstruction):
    pattern = re.compile(r'''
        \s*
        (?P<instruction>mad)
        \s+
        (?P<lval>\S+)
        \s* , \s*
        (?P<rval>
            (?P<arg1>\S+)
            \s* , \s*
            (?P<arg2>\S+)
            \s* , \s*
            (?P<arg3>\S+)
        )
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE)

    def __init__(self, text, instruction, lval, rval, arg1, arg2, arg3):
        AssignmentInstruction.__init__(self, text, instruction, lval, rval)
        self.rargs = tuple(map(lambda x: hlsltool.expression_as_single_register(x) or x, (arg1, arg2, arg3)))

class Declaration(Instruction):
    pattern = re.compile(r'''
        \s*
        dcl_.*
        $
    ''', re.MULTILINE | re.VERBOSE)

    def __eq__(self, other):
        return self.text == other.text

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

class CBDeclaration(Declaration):
    pattern = re.compile(r'''
        \s*
        dcl_constantbuffer
        \s*
        cb(?P<cb>\d+)
        \[
            (?P<size>\d+)
        \],
        \s*
        (?P<access_pattern>\S+)
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE | re.DOTALL)

    def __init__(self, text, cb, size, access_pattern):
        Declaration.__init__(self, text)
        self.cb = int(cb)
        self.size = int(size)
        self.access_pattern = access_pattern

    def __str__(self):
        return '\ndcl_constantbuffer cb%d[%d], %s' % (self.cb, self.size, self.access_pattern)

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
    CBDeclaration,
    TempsDeclaration,
    SVOutputDeclaration,
    Declaration,
    ReturnInstruction,
    SampleIndexableInstruction,
    SampleLIndexableInstruction,
    LoadStructuredInstruction,
    ResourceLoadInstruction,
    DP4Instruction,
    DP3Instruction,
    DP2Instruction,
    AddInstruction,
    MulInstruction,
    ReciprocalInstruction,
    DivInstruction,
    MADInstruction,
    MovInstruction,
    MinInstruction,
    MaxInstruction,
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

    def parse_isgn(self):
        search_str = textwrap.dedent('''
            // Input signature:
            //
            // Name                 Index   Mask Register SysValue  Format   Used
            // -------------------- ----- ------ -------- -------- ------- ------
        ''')
        signature_pattern = re.compile(r'''
            ^ \/\/
            \s+ (?P<name>\w+)
            \s+ (?P<index>\d+)
            \s+ (?P<mask>[x ][y ][z ][w ])
            \s+ (?P<register>\d+)
            \s+ (?P<sysvalue>\w+)
            \s+ (?P<format>\w+)
            \s+ (?P<used>[x ][y ][z ][w ])
        $''', re.VERBOSE)
        SignatureEntry = collections.namedtuple('Input', 'Name Index Mask Register SysValue Format Used end'.split())

        self.isgn = []

        pos = self.declarations_txt.find(search_str)
        if pos == -1:
            return

        pos = pos + len(search_str)
        while pos != -1:
            new_pos = self.declarations_txt.find('\n', pos)
            line = self.declarations_txt[pos:new_pos]

            match = signature_pattern.match(line)
            if match is None:
                return pos

            (name, index, mask, register, sysvalue, format, used) = match.groups()
            (index, register) = map(int, (index, register))
            self.isgn.append(SignatureEntry(name, index, mask, register, sysvalue, format, used, new_pos + 1))
            pos = new_pos + 1

        assert(False)

    def append_isgn_entry(self, isgn_end_pos, name, index, mask, register, sysvalue, format, used):
        #    // Name                 Index   Mask Register SysValue  Format   Used
        #    // -------------------- ----- ------ -------- -------- ------- ------
        x = '// {Name:<20} {Index:>5}   {Mask:>4} {Register:>8} {SysValue:>8} {Format:>7}   {Used:>4}\n'.format(
                Name=name, Index=index, Mask=mask, Register=register, SysValue=sysvalue, Format=format, Used=used)
        self.declarations_txt = self.declarations_txt[:isgn_end_pos] + x + self.declarations_txt[isgn_end_pos:]

    def add_ps_texcoord_input(self, texcoord, components, format='float', comment=None):
        assert(components == 1)
        self.parse_isgn()
        texcoords = filter(lambda x: x.Name == 'TEXCOORD', self.isgn)
        texcoords = sorted(texcoords, key = lambda x: x.Index)
        if list(filter(lambda x: x.Index == texcoord, texcoords)):
            raise KeyError('Shader already has TEXCOORD{}'.format(texcoord))
        last_texcoord = texcoords[-1]
        assert(last_texcoord.Mask == 'xyz ') # FIXME: Handle inserting in other cases
        assert(last_texcoord.Index < texcoord) # FIXME: Handle inserting before other texcoords
        reg_no = last_texcoord.Register # FIXME: Increment register if could not merge
        mask = '   w'
        pos = last_texcoord.end
        self.append_isgn_entry(pos, 'TEXCOORD', texcoord, mask, reg_no, 'NONE', format, mask)
        self.insert_decl()
        if comment:
            self.insert_decl('// ' + comment)
        reg = 'v{}.{}'.format(reg_no, mask.strip())
        self.insert_decl('dcl_input_ps linear ' + reg)
        return reg

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

    def remap_components(self, frm, to):
        ret = ['x'] * 4
        assert(len(frm) == len(to))
        for i in range(len(to)):
            ret[{'x': 0, 'y': 1, 'z': 2, 'w': 3}[to[i]]] = frm[i]
        return ''.join(ret)

    def hlsl_swizzle(self, mask, swizzle):
        return shadertool.asm_hlsl_swizzle(mask, swizzle)

    def mask_register(self, lval, rval):
        return hlsltool.Register(rval.negate, rval.variable, None, self.hlsl_swizzle(lval.components, rval.components))

    def find_cb_declaration(self, cb):
        for declaration in self.declarations:
            if not isinstance(declaration, CBDeclaration):
                continue
            if declaration.cb != cb:
                continue
            return declaration

    def adjust_cb_size(self, cb, size):
        declaration = self.find_cb_declaration(cb)
        if declaration:
            size = (size + 15) // 16
            if (declaration.size >= size):
                return
            debug_verbose(0, 'Resizing cb{0}[{1}] declaration to cb{0}[{2}]'.format(cb, declaration.size, size))
            declaration.size = size

    def find_cb_entry(self, type, name, used = None):
        match = self.find_header(cbuffer_entry_pattern(type, name))
        debug_verbose(2, match.group())
        offset = int(match.group('offset'))
        is_used = not match.group('unused')

        if used is not None and used != is_used:
            raise KeyError()

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

    def find_struct_entry(self, struct, type, entry):
        match = self.find_header(struct_entry_pattern(struct, type, entry))
        debug_verbose(2, match.group())
        offset = int(match.group('offset'))
        bind_name = match.group('bind_name')

        match = struct_bind_pattern(bind_name).search(self.declarations_txt, match.end())
        if match is None:
            raise KeyError()
        debug_verbose(2, match.group())

        slot = int(match.group('slot'))

        return slot, offset

    def scan_structure_loads(self, slot, offset):
        results = self.scan_shader('t%d' % slot, write=False, instr_type=LoadStructuredInstruction)
        loff = 'l(%d)' % offset
        for (line, instr) in results:
            if instr.rargs[1] == loff:
                yield (line, instr)

    def find_texture(self, name, type='texture', format=None, dim=None):
        match = self.find_header(resource_bind_pattern(name, type, format, dim))
        return 't' + match.group('slot')


    def find_col_major_matrix_multiply(shader, matrix):
        # TODO: this is quite strict at the moment, and could be relaxed to support
        # matrix multiplies that are done out of order or interleaved with
        # unrelated instructions.

        results = shader.scan_shader(matrix, write = False, instr_type = DP4Instruction)
        if len(results) != 4:
            debug_verbose(0, 'Matrix not used expected number of times')
            raise KeyError()

        # Only checks xyz go to same output variable - w often goes to another:
        if any([ r.instruction.lval.variable != results[0].instruction.lval.variable for r in results[:3] ]):
            debug_verbose(0, 'Matrix writing to differing output variables')
            raise KeyError()

        if any([ results[n].line != results[n+1].line - 1 for n in range(3) ]):
            debug_verbose(0, 'Matrix not used in sequence')
            raise KeyError()

        return results

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
            d = Declaration('\n' + declaration)
            if d not in self.declarations:
                self.declarations.append(d)
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

    def insert_ini_params(self, idx):
        if self.inserted_ini_params[idx]:
            return 0
        self.inserted_ini_params[idx] = True
        self.ini_params_reg[idx] = self.allocate_temp_reg()
        if not self.inserted_ini_params_decl:
            self.inserted_ini_params_decl = True
            self.insert_decl()
            self.insert_decl('dcl_resource_texture1d (float,float,float,float) t120', '3DMigoto IniParams:')
        off  = self.early_insert_instr()
        off += self.early_insert_instr('ld_indexable(texture1d)(float,float,float,float) {0}.xyzw, l({1}, 0, 0, 0), t120.xyzw'.format(self.ini_params_reg[idx], idx))
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

def fix_unusual_halo_with_inconsistent_w_optimisation(shader):
    # Fixes the following unusual halo pattern seen in Stranded Deep / Unity
    # 5.4, where o0 is the output position - the output position assumes that
    # the input W == 1 and optimises out the multiplication by it, yet the
    # result is then stored in a texcoord without the same optimisation.
    # add o0.xyzw, r0.xyzw, cb3[3].xyzw
    # mad r0.xyzw, cb3[3].xyzw, v0.wwww, r0.xyzw
    # mad o1.xy, v3.xyxx, cb0[13].xyxx, cb0[13].zwzz

    try:
        pos_out = shader.lookup_output_position()
    except KeyError:
        debug("Shader has no output position (tesselation?)")
        return

    results = shader.scan_shader(pos_out, components='xyzw', write=True)
    if not results:
        debug("Couldn't find write to output position register")
        return
    if len(results) > 1:
        debug_verbose(0, "Can't autofix a vertex shader writing to output position from multiple instructions")
        return
    (output_line, output_instr) = results[0]
    if not isinstance(output_instr, AddInstruction):
        debug_verbose(-1, 'Output not using add: %s' % output_instr.strip())
        return
    temp_reg, mvp_row4 = output_instr.rargs
    if not temp_reg.variable.startswith('r'):
        mvp_row4, temp_reg = temp_reg, mvp_row4
        if not temp_reg.variable.startswith('r'):
            debug_verbose(-1, 'Output not added from a temporary register and matrix: %s' % output_instr.strip())
            return
    if temp_reg.components != 'xyzw':
            debug_verbose(-1, 'Temp reg did not use all components: %s' % output_instr.strip())
            return
    if mvp_row4.components != 'xyzw':
            debug_verbose(-1, 'MVP row4 did not use all components: %s' % output_instr.strip())
            return

    results = shader.scan_shader(temp_reg.variable, components='xyzw', write=False, start=output_line + 1, stop=True)
    if not results:
        debug_verbose(-1, 'Temp register not used')
        return
    (line, instr) = results[0]
    if not isinstance(instr, MADInstruction):
        debug_verbose(-1, 'Temp register not used in mad: %s' % instr.strip())
        return
    if instr.rargs[2] != temp_reg:
        debug_verbose(-1, 'Temp register not used in expected location of mad instruction: %s' % instr.strip())
        return
    if instr.rargs[0] != mvp_row4 and instr.rargs[1] != mvp_row4:
        debug_verbose(-1, 'MVP row4 was not used in mad instruction: %s' % instr.strip())
        return

    off = shader.insert_stereo_params()

    # We could probably insert this on the following line and skip
    # adding/subtracting the 4th row, but I have a haunch this might catch a
    # few more variants if the result is directly stored in a texcoord.

    off += shader.insert_vanity_comment(line + off, 'Unusual halo fix (inconsistent W optimisation) inserted with')
    off += shader.insert_multiple_lines(line + off, '''
        add {temp_reg}.xyzw, {temp_reg}.xyzw, {mvp_row4}.xyzw
        add {stereo}.w, {temp_reg}.w, -{stereo}.y
        mad {temp_reg}.x, {stereo}.w, {stereo}.x, {temp_reg}.x
        add {temp_reg}.xyzw, {temp_reg}.xyzw, -{mvp_row4}.xyzw
    '''.format(
        temp_reg = temp_reg.variable,
        mvp_row4 = mvp_row4.variable,
        stereo = shader.stereo_params_reg
    ))

    shader.autofixed = True

def remap_cb(shader, cb, sb):
    assert(shader.shader_model.endswith('_4_0') or shader.shader_model.endswith('_5_0'))

    cb_declaration = shader.find_cb_declaration(cb)
    if not cb_declaration:
        debug_verbose(0, 'Constant buffer cb{cb} declaration not found'.format(cb=cb))
        return

    # Structured buffers max stride is 2048. While it seems to still assemble
    # and run ok if we ignore that, let's play it safe and use the structure
    # index to give us access to anything above the 2048 mark:
    stride = min(cb_declaration.size * 16, 2048)

    pattern = re.compile(r'''
        cb{cb}\[ (?P<index>\d+) \]
    '''.format(cb = cb), re.VERBOSE | re.MULTILINE)

    cb_refs = set()

    for instr in shader.instructions:
        for reg in hlsltool.find_regs_in_expression(str(instr)):
            match = pattern.match(reg.variable)
            if match:
                cb_refs.add(match.group('index'))

    if not cb_refs:
        debug_verbose(0, 'No constant buffer cb{cb} references found'.format(cb=cb))
        return

    shader.insert_decl('dcl_resource_structured t{sb}, {stride}'.format(sb = sb, stride = stride))

    shader.early_insert_vanity_comment('cb{cb} remapped to t{sb} with'.format(cb=cb, sb=sb))

    for cb_idx in sorted(map(int, cb_refs)):
        reg = shader.allocate_temp_reg()
        cb_offset = int(cb_idx) * 16
        structure_idx = cb_offset // stride
        structure_offset = cb_offset % stride
        if shader.shader_model.endswith('_4_0'):
            shader.early_insert_instr(
                'ld_structured {reg}.xyzw, l({idx}), l({offset}), t{sb}.xyzw' \
                .format(idx = structure_idx, offset = structure_offset, reg = reg, sb = sb))
        elif shader.shader_model.endswith('_5_0'):
            shader.early_insert_instr(
                'ld_structured_indexable(structured_buffer, stride={stride})(mixed,mixed,mixed,mixed) {reg}.xyzw, l({idx}), l({offset}), t{sb}.xyzw' \
                .format(idx = structure_idx, offset = structure_offset, stride = stride, reg = reg, sb = sb))
        shader.replace_reg('cb{cb}[{idx}]'.format(cb=cb, idx=cb_idx), reg)
    shader.early_insert_instr()

    shader.autofixed = True

def disable_driver_stereo_cb(shader):
    if not shader.shader_model.startswith('vs_') and not shader.shader_model.startswith('ds_'):
        debug_verbose(0, 'Disabling the driver stereo correction is only applicable to vertex and domain shaders')
        return

    cb = args.disable_driver_stereo_cb

    cb_declaration = shader.find_cb_declaration(cb)
    if cb_declaration:
        debug_verbose(0, 'Shader already declares cb{}'.format(cb))
        return

    shader.insert_decl('// Disables driver stereo correction:')
    shader.insert_decl('dcl_constantbuffer cb{}[4], immediateIndexed'.format(cb))

    # Not counting this as autofixed since we expect to be doing something else
    # as well. Important for UE4 autofix script.

def fix_unity_lighting_ps(shader):
    if args.fix_unity_lighting_ps[:-1] != 'TEXCOORD':
        debug('ERROR: --fix-unity-lighting-ps must take a TEXCOORD')
        return

    try:
        _CameraToWorld = cb_matrix(*shader.find_unity_cb_entry(shadertool.unity_CameraToWorld, 'matrix'))
        _ZBufferParams_cb, _ZBufferParams_offset = shader.find_unity_cb_entry(shadertool.unity_ZBufferParams, 'constant')
        _ZBufferParams = cb_offset(_ZBufferParams_cb, _ZBufferParams_offset)
    except KeyError:
        debug_verbose(0, 'Shader does not have all required values for the Unity lighting fix')
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

    debug_verbose(0, '_CameraToWorld in %s, _ZBufferParams in %s' % (_CameraToWorld, _ZBufferParams))

    fov_reg = shader.add_ps_texcoord_input(int(args.fix_unity_lighting_ps[-1]), 1,
            comment='New input from vertex shader with unity_CameraInvProjection[0].x:')

    fix_unity_reflection(shader, fov_reg, _CameraToWorld)

    # Find _CameraToWorld usage - adjustment must be above this point, and this
    # gives us the register with X that needs to be adjusted:
    x_var, _CameraToWorld_line = shader.find_var_component_from_row_major_matrix_multiply(_CameraToWorld[0])

    # Since the compiler often places y first, for clarity use it's position to insert the correction:
    _, line_y = shader.find_var_component_from_row_major_matrix_multiply(_CameraToWorld[1])
    _CameraToWorld_line = min(_CameraToWorld_line, line_y)

    # And once more to find register with Z to use as depth:
    depth, line_z = shader.find_var_component_from_row_major_matrix_multiply(_CameraToWorld[2])
    #offset = shader.insert_instr(line_z, comment='depth in %s:' % depth)
    depth_reg = hlsltool.expression_as_single_register(depth)

    # And to find the end for the fallback world space adjustment:
    _, _CameraToWorld_end = shader.find_var_component_from_row_major_matrix_multiply(_CameraToWorld[3])
    _CameraToWorld_end = max(_CameraToWorld_end, line_z, line_y, _CameraToWorld_line)
    world_reg = hlsltool.expression_as_single_register(shader.instructions[_CameraToWorld_end].lval)

    # Find _ZBufferParams usage to find where depth is sampled (could use
    # _CameraDepthTexture, but that takes an extra step and more can go wrong)
    results = shader.scan_shader(_ZBufferParams, write=False, end=_CameraToWorld_line)
    if len(results) != 1:
        # XXX: In shadertool.py scan_shader returns the two reads on the one
        # instruction, currently we only return one per instruction
        debug_verbose(0, '_ZBufferParams read %i times (only exactly 1 reads currently supported)' % len(results))
        return
    (line, instr) = results[0]
    reg = hlsltool.expression_as_single_register(instr.lval)

    # We're expecting a reciprocal calculation as part of the Z buffer -> world
    # Z scaling:
    results = shader.scan_shader(reg.variable, components=reg.components, instr_type=ReciprocalInstruction,
            write=False, start=line+1, end=_CameraToWorld_line, stop=True)
    if not results:
        debug_verbose(0, 'Could not find expected reciprocal instruction')
        return
    (line, instr) = results[0]
    reg = hlsltool.expression_as_single_register(instr.lval)

    # Find where the reciprocal is next used:
    results = shader.scan_shader(reg.variable, components=reg.components, write=False,
            start=line+1, end=_CameraToWorld_line, stop=True)
    if not results:
        debug_verbose(0, 'Could not find expected instruction')
        return
    (line, instr) = results[0]
    reg = hlsltool.expression_as_single_register(instr.lval)

    # We used to trace the function forwards more here, but Dreamfall Chapters
    # got complicated after the Unity 5 update. Now we find the depth from the
    # matrix multiply instead, which hopefully should be more robust.

    # If we ever need the old procedure, it's in the git history of shadertool.py.

    # Find where the depth was set and store it in a variable:
    results = shader.scan_shader(depth_reg.variable, components=depth_reg.components, write=True,
            start=line_z - 1, end=line-1, stop=True, direction=-1)
    if not results:
        debug_verbose(0, 'Could not find where depth was set')
        return
    (depth_line, _) = results[0]

    shader.insert_decl('dcl_constantbuffer cb10[4], immediateIndexed') # Inversed VP
    off = shader.insert_stereo_params()

    depth_reg = shader.allocate_temp_reg()
    off += shader.insert_multiple_lines(depth_line + off + 1, '''
        // copy depth from {depth} to {depth_reg}.x:
        mov {depth_reg}.x, {depth}
    '''.format(
        depth = depth,
        depth_reg = depth_reg,
    ))

    clip_space_adj = shader.allocate_temp_reg()

    off = _CameraToWorld_line + off
    debug_verbose(-1, 'Line %i: Applying Unity pixel shader light/shadow fix. depth in %s, x in %s' % (off, depth, x_var))
    off += shader.insert_vanity_comment(off, "Unity light/shadow fix (pixel shader stage) inserted with")
    off += shader.insert_multiple_lines(off, '''
        add {clip_space_adj}.x, {depth}.x, -{stereo}.y
        mul {clip_space_adj}.x, {stereo}.x, {clip_space_adj}.x
        ne {stereo}.w, l(0.0, 0.0, 0.0, 0.0), {fov_reg}
        if_nz {stereo}.w
          mad {x_var}, -{clip_space_adj}.x, {fov_reg}, {x_var}
        endif
    '''.format(
        depth = depth_reg,
        stereo = shader.stereo_params_reg,
        clip_space_adj = clip_space_adj,
        fov_reg = fov_reg,
        x_var = x_var,
    ))

    off = off - _CameraToWorld_line + _CameraToWorld_end + 1
    off += shader.insert_multiple_lines(off, '''
        if_z {stereo}.w
          mad {world_var}.{world_mask}, -{clip_space_adj}.xxxx, {InvVPMatrix0}.{world_adj_swizzle}, {world_var}.xyzw
        endif
    '''.format(
        depth = depth_reg,
        stereo = shader.stereo_params_reg,
        clip_space_adj = clip_space_adj,
        InvVPMatrix0 = 'cb10[0]',
        world_var = world_reg.variable,
        world_mask = world_reg.components[:3],
        world_adj_swizzle = shader.remap_components('xyz', world_reg.components[:3]),
        fov_reg = fov_reg,
    ))

    shader.add_shader_override_setting('%s-cb10 = Resource_Inverse_VP_CB' % (shader.shader_type));

    if has_unity_headers and _CameraDepthTexture is not None:
        shader.add_shader_override_setting('Resource_CameraDepthTexture = ps-%s' % _CameraDepthTexture);
        shader.add_shader_override_setting('Resource_UnityPerCamera = ps-cb%d' % _ZBufferParams_cb);

    shader.autofixed = True

def fix_unity_reflection(shader, fov_reg = None, _CameraToWorld = None):
    try:
        _WorldSpaceCameraPos = cb_offset(*shader.find_unity_cb_entry(shadertool.unity_WorldSpaceCameraPos, 'constant'))
    except KeyError:
        debug_verbose(0, 'Shader does not use _WorldSpaceCameraPos')
        return

    shader.insert_decl('dcl_constantbuffer cb10[4], immediateIndexed') # Inversed VP

    shader.insert_stereo_params()

    repl_WorldSpaceCameraPos = shader.allocate_temp_reg()

    # Apply a stereo correction to the world space camera position - this
    # pushes environment reflections, specular highlights, etc to the correct
    # depth
    shader.replace_reg(_WorldSpaceCameraPos, repl_WorldSpaceCameraPos, 'xyz')
    shader.early_insert_vanity_comment("Unity reflection/specular fix inserted with")
    if fov_reg is None:
        shader.early_insert_multiple_lines('''
            mul {stereo}.w, -{stereo}.x, {stereo}.y
            mad {repl_WorldSpaceCameraPos}.xyz, -{stereo}.wwww, {InvVPMatrix0}.xyzw, {_WorldSpaceCameraPos}.xyzw
        '''.format(
            _WorldSpaceCameraPos = _WorldSpaceCameraPos,
            repl_WorldSpaceCameraPos = repl_WorldSpaceCameraPos,
            stereo = shader.stereo_params_reg,
            InvVPMatrix0 = 'cb10[0]',
        ))
    else:
        tmp = shader.allocate_temp_reg()
        shader.early_insert_multiple_lines('''
            mul {stereo}.w, -{stereo}.x, {stereo}.y
            ne {tmp}.x, l(0.0, 0.0, 0.0, 0.0), {fov_reg}
            if_nz {tmp}.x
              mul {stereo}.w, {stereo}.w, {fov_reg}
              mad {repl_WorldSpaceCameraPos}.xyz, -{stereo}.wwww, {_CameraToWorld0}.xyzw, {_WorldSpaceCameraPos}.xyzw
            else
              mad {repl_WorldSpaceCameraPos}.xyz, -{stereo}.wwww, {InvVPMatrix0}.xyzw, {_WorldSpaceCameraPos}.xyzw
            endif
        '''.format(
            _WorldSpaceCameraPos = _WorldSpaceCameraPos,
            repl_WorldSpaceCameraPos = repl_WorldSpaceCameraPos,
            stereo = shader.stereo_params_reg,
            tmp = tmp,
            fov_reg = fov_reg,
            _CameraToWorld0 = _CameraToWorld[0],
            InvVPMatrix0 = 'cb10[0]',
        ))

    if hlsltool.possibly_copy_unity_world_matrices(shader):
        shader.add_shader_override_setting('run = CustomShader_Inverse_Unity_MVP')

    shader.add_shader_override_setting('%s-cb10 = Resource_Inverse_VP_CB' % (shader.shader_type));

    shader.autofixed = True

def fix_unity_frustum_world(shader):
    try:
        _FrustumCornersWS = cb_matrix(*shader.find_unity_cb_entry(shadertool.unity_FrustumCornersWS, 'matrix'))
    except KeyError:
        debug_verbose(0, 'Shader does not use _FrustumCornersWS, or is missing headers (my other scripts can extract these)')
        return

    shader.insert_decl('dcl_constantbuffer cb10[4], immediateIndexed') # Inversed VP
    shader.insert_decl('dcl_constantbuffer cb13[9], immediateIndexed') # UnityPerCamera

    shader.insert_stereo_params()

    repl_FrustumCornersWS = []
    for i in range(3):
        repl_FrustumCornersWS.append(shader.allocate_temp_reg())
        shader.replace_reg(_FrustumCornersWS[i], repl_FrustumCornersWS[i], 'xyzw')

    far = shader.allocate_temp_reg()
    clip_space_adj = shader.allocate_temp_reg()
    world_space_adj = shader.allocate_temp_reg()

    # Apply a stereo correction to the world space frustum corners - this
    # fixes the glow around the sun in The Forest (shaders called Sunshine
    # PostProcess Scatter)
    shader.early_insert_vanity_comment("Unity _FrustumCornersWS fix inserted with")
    shader.early_insert_multiple_lines('''
        add {far}.x, {_ZBufferParams}.z, {_ZBufferParams}.w
        rcp {far}.x, {far}.x
        add {clip_space_adj}.x, {far}.x, -{stereo}.y
        mul {clip_space_adj}.x, {stereo}.x, {clip_space_adj}.x
        mul {world_space_adj}.xyzw, {InvVPMatrix0}.xyzw, {clip_space_adj}.xxxx
        // GOTCHA: _FrustumCornersWS is TRANSPOSED vs DX9!
        add {repl_FrustumCornersWS0}.xyzw, {_FrustumCornersWS0}.xyzw, -{world_space_adj}.xxxx
        add {repl_FrustumCornersWS1}.xyzw, {_FrustumCornersWS1}.xyzw, -{world_space_adj}.yyyy
        add {repl_FrustumCornersWS2}.xyzw, {_FrustumCornersWS2}.xyzw, -{world_space_adj}.zzzz
    '''.format(
        far = far,
        _ZBufferParams = 'cb13[7]',
        stereo = shader.stereo_params_reg,
        clip_space_adj = clip_space_adj,
        world_space_adj = world_space_adj,
        InvVPMatrix0 = 'cb10[0]',
        repl_FrustumCornersWS0 = repl_FrustumCornersWS[0],
        repl_FrustumCornersWS1 = repl_FrustumCornersWS[1],
        repl_FrustumCornersWS2 = repl_FrustumCornersWS[2],
        _FrustumCornersWS0 = _FrustumCornersWS[0],
        _FrustumCornersWS1 = _FrustumCornersWS[1],
        _FrustumCornersWS2 = _FrustumCornersWS[2],
    ))

    shader.add_shader_override_setting('%s-cb10 = Resource_Inverse_VP_CB' % (shader.shader_type));
    shader.add_shader_override_setting('%s-cb13 = Resource_UnityPerCamera' % (shader.shader_type));

    shader.autofixed = True

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

    # Do not adjust camra position. Fixes the reflection of the sun, but
    # damages some water shades with caustics (e.g. c9999f0efe46b6cb in first
    # mammoth mission). May be able to use corrected + uncorrected coordinates
    # to fix both, but trickier to script.
    # fix_fcprimal_camera_pos(shader)

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
    depth_reg = depth_instr.lval

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

    fix_fcprimal_camera_pos(shader)

    # Copying from these shaders is not working - need to investigate why:
    # shader.set_ini_name('PhysicalLighting')
    # shader.add_shader_override_setting('ResourceDepthBuffer = stereo2mono ps-%s' % Depth)
    # shader.add_shader_override_setting('ResourceCViewportShaderParameterProvider = ps-cb%d' % DepthScale.cb)

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

def _fix_volumetric_fog(shader, CameraPosition, ViewProjectionMatrix, InvProjectionMatrix, InvViewMatrix):
    # FIXME: Verify something exists in the shader to confirm this is
    # volumetric fog, otherwise it applies to anything using CameraPosition

    results = shader.scan_shader(CameraPosition, write=False)
    if not results:
        debug_verbose(0, 'Shader does not use CameraPosition')
        return

    try:
        VFPrevWorldToVolumetricShadowMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'VFPrevWorldToVolumetricShadowMatrix'))
    except:
        VFPrevWorldToVolumetricShadowMatrix = None

    off = 0

    for (line, instr) in results:
        pos = instr.lval
        if len(pos.components) != 3:
            continue

        if off == 0:
            off  = shader.insert_stereo_params()
            tmp1 = shader.allocate_temp_reg()
            tmp2 = shader.allocate_temp_reg()

        off += shader.insert_vanity_comment(line + off + 1, 'Volumetric Fog fix inserted with')

        # Removes smear from shadow volume shaders:
        if VFPrevWorldToVolumetricShadowMatrix is not None:
            p_results = shader.scan_shader(VFPrevWorldToVolumetricShadowMatrix, start = line + 1, write = False)
            if p_results:
                orig_pos = shader.allocate_temp_reg()
                for (p_line, p_instr) in p_results:
                     shader.replace_rval_reg_on_line(p_line, pos.variable, orig_pos)
                off += shader.insert_multiple_lines(line + off + 1, '''
                    mov {orig_pos}.xyzw, {pos}.xyzw
                    mov {orig_pos}.w, l(1.0)
                '''.format(
                    orig_pos = orig_pos,
                    pos = pos.variable,
                ))

        off += shader.insert_multiple_lines(line + off + 1, '''
            mov {tmp1}.xyz, {pos}.{pos_swizzle}
            mov {tmp1}.w, l(1.0)
            dp4 {tmp2}.w, {tmp1}.xyzw, {ViewProjectionMatrix3}.xyzw
            add {tmp2}.x, {tmp2}.w, -{stereo}.y
            mul {tmp2}.x, {tmp2}.x, -{stereo}.x
            mul {tmp2}.x, {tmp2}.x, {InvProjectionMatrix0}.x
            mov {tmp2}.yzw, l(0.0)
            dp4 {tmp1}.x, {tmp2}.xyzw, {InvViewMatrix0}.xyzw
            dp4 {tmp1}.y, {tmp2}.xyzw, {InvViewMatrix1}.xyzw
            dp4 {tmp1}.z, {tmp2}.xyzw, {InvViewMatrix2}.xyzw
            add {pos}.{pos_mask}, {pos}.xyzw, {tmp1}.{adj_swizzle}
        '''.format(
            pos = pos.variable,
            pos_mask = pos.components,
            pos_swizzle = shader.remap_components(pos.components, 'xyz'),
            adj_swizzle = shader.remap_components('xyz', pos.components),
            stereo = shader.stereo_params_reg,
            ViewProjectionMatrix3 = ViewProjectionMatrix[3],
            InvProjectionMatrix0 = InvProjectionMatrix[0],
            InvViewMatrix0 = InvViewMatrix[0],
            InvViewMatrix1 = InvViewMatrix[1],
            InvViewMatrix2 = InvViewMatrix[2],
            tmp1=tmp1,
            tmp2=tmp2
        ))

        shader.autofixed = True

def fix_fcprimal_volumetric_fog(shader):
    try:
        CameraPosition = cb_offset(*shader.find_cb_entry('float3', 'CameraPosition'))
        ViewProjectionMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'ViewProjectionMatrix'))
        InvProjectionMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'InvProjectionMatrix'))
        InvViewMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'InvViewMatrix'))
    except KeyError:
        debug_verbose(0, 'Shader does not declare all required values for the Far Cry Primal volumetric fog adjustment')
        return

    return _fix_volumetric_fog(shader, CameraPosition, ViewProjectionMatrix, InvProjectionMatrix, InvViewMatrix)

def fix_wd2_volumetric_fog(shader):
    try:
        CameraPosition = cb_offset(*shader.find_cb_entry('float3', 'CameraPosition'))
        ViewProjectionMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'ViewProjectionMatrix'))
        InvProjectionMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'InvProjectionMatrix'))
        InvViewMatrix = cb_matrix(*shader.find_cb_entry('float4x3', 'InvViewMatrix'))
    except KeyError:
        debug_verbose(0, 'Shader does not declare all required values for the WATCH_DOGS2 volumetric fog adjustment')
        return

    _fix_volumetric_fog(shader, CameraPosition, ViewProjectionMatrix, InvProjectionMatrix, InvViewMatrix)

def fix_wd2_view_dir_reconstruction(shader):
    # Separated out from fix_wd2_volumetric_fog as it was found to completely
    # break volumetric fog around light sources on foggy nights
    # (f444d56ce15ac78e). Need to only apply this to sun/moon fog shaders (or
    # find a better way to adjust them that works for everything).
    #
    # Not positive if FVViewDirReconstruction ever needs to be adjusted, but
    # adding it here so we can easily test.
    for name in ('VFViewDirReconstruction', 'FVViewDirReconstruction'):
        try:
            ViewDirReconstruction = cb_offset(*shader.find_cb_entry('float4', name))
        except KeyError:
            debug_verbose(0, 'Shader does not declare %s' % name)
            continue

        results = shader.scan_shader(ViewDirReconstruction, components='x', write=False)
        if len(results) != 1:
            debug_verbose(0, 'Shader does not use %s' % name)
            continue
        line, instr = results[0]

        off = shader.insert_stereo_params()

        off += shader.insert_vanity_comment(line + off, '%s adjustement (sun/moon volumetric fog) inserted with' % name)
        shader.insert_multiple_lines(line + off, '''
            add {x}, {x}, -{stereo}.x
        '''.format(
            x = instr.lval.variable + '.x',
            stereo = shader.stereo_params_reg,
        ))

        shader.autofixed = True

def fix_wd2_camera_z_axis(shader, multiplier):
    # Experimental alternate method to fix volumetric fog when used in
    # conjunction with --fix-wd2-view-dir-reconstruction by adjusting the
    # camera Z axis to match the off-center projection (i.e. by separation).
    # Does have slightly different results to the regular fix, but hard to say
    # if it is better or worse. This cancels out the sun/moon glow adjustment
    # though, so it can't be used with those shaders.

    neg = {-1: '-', 1: ''}[multiplier]

    for name in ('VFCameraZAxis', 'FVCameraZAxis'):
        try:
            CameraZAxis = cb_offset(*shader.find_cb_entry('float3', name, used = True))
            InvProjectionMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'InvProjectionMatrix'))
            InvViewMatrix = cb_matrix(*shader.find_cb_entry('float4x3', 'InvViewMatrix'))
        except KeyError:
            debug_verbose(0, 'Shader does not declare/use %s' % name)
            continue

        off = shader.insert_stereo_params()
        repl_CameraZAxis = shader.allocate_temp_reg()
        tmp1 = shader.allocate_temp_reg()
        tmp2 = shader.allocate_temp_reg()

        shader.replace_reg(CameraZAxis, repl_CameraZAxis, 'xyz')
        shader.early_insert_vanity_comment('WATCH_DOGS2 %s adjustment inserted with' % name)
        shader.early_insert_multiple_lines('''
            mul {tmp1}.x, {stereo}.x, {InvProjectionMatrix0}.x
            mul {tmp1}.y, {stereo}.x, {InvProjectionMatrix1}.x
            mul {tmp1}.z, {stereo}.x, {InvProjectionMatrix2}.x
            mul {tmp1}.w, {stereo}.x, {InvProjectionMatrix3}.x
            dp4 {tmp2}.x, {tmp1}.xyzw, {InvViewMatrix0}.xyzw
            dp4 {tmp2}.y, {tmp1}.xyzw, {InvViewMatrix1}.xyzw
            dp4 {tmp2}.z, {tmp1}.xyzw, {InvViewMatrix2}.xyzw
            add {repl_CameraZAxis}.xyz, {CameraZAxis}.xyz, {neg}{tmp2}.xyz
        '''.format(
            stereo = shader.stereo_params_reg,
            InvProjectionMatrix0 = InvProjectionMatrix[0],
            InvProjectionMatrix1 = InvProjectionMatrix[1],
            InvProjectionMatrix2 = InvProjectionMatrix[2],
            InvProjectionMatrix3 = InvProjectionMatrix[3],
            InvViewMatrix0 = InvViewMatrix[0],
            InvViewMatrix1 = InvViewMatrix[1],
            InvViewMatrix2 = InvViewMatrix[2],
            CameraZAxis = CameraZAxis,
            repl_CameraZAxis = repl_CameraZAxis,
            tmp1 = tmp1,
            tmp2 = tmp2,
            neg = neg,
        ))

        shader.autofixed = True

def fix_fcprimal_light_pos(shader):
    try:
        LightingData_pos = shader.find_struct_entry('LightingData', 'float4', 'pos')
        ViewProjectionMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'ViewProjectionMatrix'))
        InvProjectionMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'InvProjectionMatrix'))
        InvViewMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'InvViewMatrix'))
    except KeyError:
        debug_verbose(0, 'Shader does not declare all required values for the Far Cry Primal light position adjustment')
        return

    off = 0
    for (i, (line, instr)) in enumerate(shader.scan_structure_loads(*LightingData_pos)):
        if i == 0:
            off += shader.insert_stereo_params()
            tmp1 = shader.allocate_temp_reg()
            tmp2 = shader.allocate_temp_reg()

        pos = instr.lval

        off += shader.insert_vanity_comment(line + off + 1, 'LightsLightingData.pos (Volumetric Fog) adjustment inserted with')
        off += shader.insert_multiple_lines(line + off + 1, '''
            mov {tmp1}.xyz, {pos}.{pos_swizzle}
            mov {tmp1}.w, l(1.0)
            dp4 {tmp2}.w, {tmp1}.xyzw, {ViewProjectionMatrix3}.xyzw
            add {tmp2}.x, {tmp2}.w, -{stereo}.y
            mul {tmp2}.x, {tmp2}.x, {stereo}.x
            mul {tmp2}.x, {tmp2}.x, {InvProjectionMatrix0}.x
            mov {tmp2}.yzw, l(0.0)
            dp4 {tmp1}.x, {tmp2}.xyzw, {InvViewMatrix0}.xyzw
            dp4 {tmp1}.y, {tmp2}.xyzw, {InvViewMatrix1}.xyzw
            dp4 {tmp1}.z, {tmp2}.xyzw, {InvViewMatrix2}.xyzw
            add {pos}.{pos_mask}, {pos}.xyzw, {tmp1}.{adj_swizzle}
        '''.format(
            pos = pos.variable,
            pos_mask = pos.components,
            pos_swizzle = shader.remap_components(pos.components, 'xyz'),
            adj_swizzle = shader.remap_components('xyz', pos.components),
            stereo = shader.stereo_params_reg,
            ViewProjectionMatrix3 = ViewProjectionMatrix[3],
            InvProjectionMatrix0 = InvProjectionMatrix[0],
            InvViewMatrix0 = InvViewMatrix[0],
            InvViewMatrix1 = InvViewMatrix[1],
            InvViewMatrix2 = InvViewMatrix[2],
            tmp1=tmp1,
            tmp2=tmp2
        ))

        shader.autofixed = True

def fix_wd2_unproject_main(shader, allow_multiple=False):
    try:
        InvProjectionMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'InvProjectionMatrix'))
        VPosScale = cb_offset(*shader.find_cb_entry('float4', 'VPosScale'))
        VPosOffset = cb_offset(*shader.find_cb_entry('float4', 'VPosOffset'))
    except KeyError:
        debug_verbose(0, 'Shader does not declare all required values for the regular WATCH_DOGS2 unprojection fix')
        return


    # Scan for:
    # r2.x = dot(r0.zw, InvProjectionMatrix._m22_m32);
    # r0.z = dot(r0.zw, InvProjectionMatrix._m23_m33);
    r2 = shader.scan_shader(InvProjectionMatrix[2], write=False, instr_type=DP2Instruction)
    r3 = shader.scan_shader(InvProjectionMatrix[3], write=False, instr_type=DP2Instruction)
    if len(r2) == 0 or len(r3) == 0:
        debug_verbose(0, 'Shader does not use InvProjectionMatrix')
        return
    if not allow_multiple and (len(r2) > 1 or len(r3) > 1):
        debug_verbose(0, 'Shader uses InvProjectionMatrix more than once')
        return
    line = max(r2[0].line, r3[0].line) + 1

    # Scan for:
    # r0.z = -r2.x / r0.z;
    r2 = shader.scan_shader(r2[0].instruction.lval, start=line, write=False, stop=True, stop_when_clobbered=True, instr_type=DivInstruction)
    r3 = shader.scan_shader(r3[0].instruction.lval, start=line, write=False, stop=True, stop_when_clobbered=True, instr_type=DivInstruction)
    if len(r2) != 1 or len(r3) != 1 or r2[0].line != r3[0].line:
        debug_verbose(0, 'Depth calculation does not follow expected pattern (1)')
        return
    line, instr = r2[0]
    depth_reg = instr.lval
    if instr.rargs[0].negate == instr.rargs[1].negate:
        # XXX Wouldn't surprise me if this is not universal, but start specific then generalise...
        debug_verbose(0, 'Depth calculation does not follow expected pattern (2)')
        return

    # Scan for possible negate:
    # r2.z = -r0.z;
    r = shader.scan_shader(depth_reg, start=line + 1, write=False, stop=True, stop_when_clobbered=True, stop_when_read=True, instr_type=MovInstruction)
    if r:
        line, instr = r[0]
        if not instr.rarg.negate:
            debug_verbose(0, 'Depth calculation does not follow expected pattern (4)')
            return
        depth_reg = -instr.lval

    # Scan for
    # min r0.w, r0.w, r1.x
    r = shader.scan_shader(depth_reg, start=line + 1, write=False, stop=True, stop_when_clobbered=True, stop_when_read=True, instr_type=MinInstruction)
    if r:
        line, instr = r[0]
        depth_reg = instr.lval

    # Scan for
    # r2.xy = r2.zz * r0.xy;
    r = shader.scan_shader(depth_reg, start=line + 1, write=False, stop=True, stop_when_clobbered=True, instr_type=MulInstruction)
    if len(r) != 1:
        debug_verbose(0, 'Depth calculation does not follow expected pattern (5)')
        return

    prev_depth_reg = depth_reg
    if r[0].instruction.rargs[0].negate != r[0].instruction.rargs[1].negate:
        depth_reg = -depth_reg

    line, instr = r[0]
    vpos = instr.lval

    # removed - b474742570c37446 and compute shaders do not follow this pattern:
    # # Scan up for r0.xy = v0.xy * VPosScale.zw + VPosOffset.zw;

    off = shader.insert_stereo_params()

    debug("vpos in {} depth in {}".format(vpos, depth_reg))
    if hlsltool.regs_overlap(vpos, depth_reg.variable, depth_reg.components):
        off += shader.insert_instr(line + off)
        off += shader.insert_instr(line + off,
                'mov {stereo}.w, {depth}'.format(
                    stereo = shader.stereo_params_reg,
                    depth = prev_depth_reg
                ), 'Save off depth before it is clobbered:')
        off += shader.insert_instr(line + off)
        debug("vpos in {} and depth in {} overlap - remapping".format(vpos, depth_reg))
        depth_reg = shader.stereo_params_reg + '.w'

    off += shader.insert_vanity_comment(line + off + 1, 'WATCH_DOGS2 unprojection fix inserted with')

    off += shader.insert_multiple_lines(line + off + 1, '''
        add {stereo}.w, {depth}, -{stereo}.y
        mul {stereo}.w, {stereo}.w, {stereo}.x
        mad {vpos}.{vpos_x}, -{stereo}.w, {InvProjectionMatrix0}.x, {vpos}.{vpos_x}
    '''.format(
        vpos = vpos.variable,
        vpos_x = vpos.components[0],
        depth = depth_reg,
        stereo = shader.stereo_params_reg,
        InvProjectionMatrix0 = InvProjectionMatrix[0],
    ))

    shader.autofixed = True
    shader.wd2_unprojection_fix_applied = True

def fix_wd2_unproject_ansel(shader, allow_multiple=False):
    try:
        InvProjectionMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'InvProjectionMatrix'))
    except KeyError:
        debug_verbose(0, 'Shader does not declare all required values for the Ansel WATCH_DOGS2 unprojection fix')
        return

    # Ansel shaders use a full multiplication with the inverse projection
    # matrix instead of the partial multiplication that the regular variants of
    # the shaders use. Light shaders also only dump on demand while Ansel is
    # loaded, making it diffult to do an offline fix for these, but we can
    # still script the pattern

    # FIXME: This is basically the same as the soft shadow fix, except the
    # shaders have headers, Z is negated, the div may only use three
    # components. Should be able to refactor these together
    try:
        matrix_results = shader.find_col_major_matrix_multiply(InvProjectionMatrix)
    except KeyError:
        return
    line, instr = matrix_results[3]

    results = shader.scan_shader(instr.lval.variable, start = line + 1, write = False, stop = True, stop_when_clobbered = True, instr_type = DivInstruction)
    if not results or results[0].line != line + 1 or \
            len(results[0].instruction.lval.components) < 3 or \
            not hlsltool.regs_overlap(results[0].instruction.rargs[0], matrix_results[0].instruction.lval.variable, 'xyz'):
        debug_verbose(0, 'Inverse projection matrix normalisation not in expected location')
        return
    line, instr = results[0]
    vpos = instr.lval.variable

    off = shader.insert_stereo_params()
    off += shader.insert_vanity_comment(line + off + 1, 'WATCH_DOGS2 unprojection (NVIDIA Ansel variant) fix inserted with')
    off += shader.insert_multiple_lines(line + off + 1, '''
        add {stereo}.w, -{vpos}.z, -{stereo}.y
        mul {stereo}.w, {stereo}.w, {stereo}.x
        mad {vpos}.x, -{stereo}.w, {InvProjectionMatrix0}.x, {vpos}.x
    '''.format(
        stereo = shader.stereo_params_reg,
        InvProjectionMatrix0 = InvProjectionMatrix[0],
        vpos = vpos,
    ))

    shader.autofixed = True
    shader.wd2_unprojection_fix_applied = True

def fix_wd2_unproject(shader, allow_multiple=False):
    if hasattr(shader, 'wd2_unprojection_fix_applied'):
        return

    fix_wd2_unproject_main(shader, allow_multiple)
    fix_wd2_unproject_ansel(shader, allow_multiple)

def fix_wd2_camera_pos(shader, limit = None, exclude = None):
    if hasattr(shader, 'wd2_camera_pos_fix_applied'):
        return

    try:
        InvProjectionMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'InvProjectionMatrix'))
        InvViewMatrix = cb_matrix(*shader.find_cb_entry('float4x3', 'InvViewMatrix'))
    except KeyError:
        debug_verbose(0, 'Shader does not declare all required values for the WATCH_DOGS2 camera position fix')
        return

    for name in ('CameraPosition', 'VFCameraPosition'):
        try:
            CameraPosition = cb_offset(*shader.find_cb_entry('float3', name, used = True))
        except KeyError:
            debug_verbose(0, 'Shader does not declare/use %s' % name)
            continue

        off = shader.insert_stereo_params()
        repl_CameraPosition = shader.allocate_temp_reg()
        tmp1 = shader.allocate_temp_reg()
        tmp2 = shader.allocate_temp_reg()

        shader.replace_reg(CameraPosition, repl_CameraPosition, 'xyz', limit = limit, start = exclude)
        shader.early_insert_vanity_comment('WATCH_DOGS2 %s adjustment inserted with' % name)
        shader.early_insert_multiple_lines('''
            mul {stereo}.w, {stereo}.x, {stereo}.y
            mul {tmp1}.x, {stereo}.w, {InvProjectionMatrix0}.x
            mul {tmp1}.y, {stereo}.w, {InvProjectionMatrix1}.x
            mul {tmp1}.z, {stereo}.w, {InvProjectionMatrix2}.x
            mul {tmp1}.w, {stereo}.w, {InvProjectionMatrix3}.x
            dp4 {tmp2}.x, {tmp1}.xyzw, {InvViewMatrix0}.xyzw
            dp4 {tmp2}.y, {tmp1}.xyzw, {InvViewMatrix1}.xyzw
            dp4 {tmp2}.z, {tmp1}.xyzw, {InvViewMatrix2}.xyzw
            add {repl_CameraPosition}.xyz, {CameraPosition}.xyz, {tmp2}.xyz
        '''.format(
            stereo = shader.stereo_params_reg,
            InvProjectionMatrix0 = InvProjectionMatrix[0],
            InvProjectionMatrix1 = InvProjectionMatrix[1],
            InvProjectionMatrix2 = InvProjectionMatrix[2],
            InvProjectionMatrix3 = InvProjectionMatrix[3],
            InvViewMatrix0 = InvViewMatrix[0],
            InvViewMatrix1 = InvViewMatrix[1],
            InvViewMatrix2 = InvViewMatrix[2],
            CameraPosition = CameraPosition,
            repl_CameraPosition = repl_CameraPosition,
            tmp1 = tmp1,
            tmp2 = tmp2,
        ))

        shader.autofixed = True
        shader.wd2_camera_pos_fix_applied = True

def fix_wd2_screen_space_reflections(shader):
    try:
        CameraPosition = cb_offset(*shader.find_cb_entry('float3', 'CameraPosition'))
        ViewportSize = cb_offset(*shader.find_cb_entry('float4', 'ViewportSize'))
        InvProjectionMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'InvProjectionMatrix'))
        ProjectionMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'ProjectionMatrix'))
        CameraSpaceToPreviousProjectedSpace = cb_matrix(*shader.find_cb_entry('float4x4', 'CameraSpaceToPreviousProjectedSpace'))
        ProjectToPixelMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'ProjectToPixelMatrix'))
    except KeyError:
        debug_verbose(0, 'Shader does not declare all required values for the WATCH_DOGS2 screen space reflection fix')
        return

    shader.insert_stereo_params()
    shader.early_insert_vanity_comment("WATCH_DOGS2 Screen Space Reflection fix inserted with")

    # The unprojection fix applies several times in this shader, but we currently
    # only fix the first as the others make no noticeable difference and their
    # instructions aren't quite the same (can add them later if needed):
    fix_wd2_unproject(shader, allow_multiple=True)

    # The camera position fix has the effect of moving the screen space
    # reflections from surface depth to correct depth (once all other
    # adjustments are in place to get them to the surface depth):
    fix_wd2_camera_pos(shader)

    off = 0
    for line, instr in shader.scan_shader(ProjectionMatrix[3], write = False):
        x_line, x_instr = shader.scan_shader(ProjectionMatrix[0], start = line + off - 1, direction = -1, stop = True, write = False)[0]
        off += shader.insert_multiple_lines(line + off + 1, '''
            // ProjectionMatrix - standard stereo correction:
            add {stereo}.w, {depth}, -{stereo}.y
            mad {x}, {stereo}.w, {stereo}.x, {x}
        '''.format(
            stereo = shader.stereo_params_reg,
            depth = instr.lval,
            x = x_instr.lval,
        ))

    off = 0
    for line, instr in shader.scan_shader(CameraSpaceToPreviousProjectedSpace[3], write = False):
        x_line, x_instr = shader.scan_shader(CameraSpaceToPreviousProjectedSpace[0], start = line + off - 1, direction = -1, stop = True, write = False)[0]
        off += shader.insert_multiple_lines(line + off + 1, '''
            // CameraSpaceToPreviousProjectedSpace - standard stereo correction:
            add {stereo}.w, {depth}, -{stereo}.y
            mad {x}, {stereo}.w, {stereo}.x, {x}
        '''.format(
            stereo = shader.stereo_params_reg,
            depth = instr.lval,
            x = x_instr.lval,
        ))

    off = 0
    for line, instr in shader.scan_shader(ProjectToPixelMatrix[3], write = False):
        x_line, x_instr = shader.scan_shader(ProjectToPixelMatrix[0], start = line + off - 1, direction = -1, stop = True, write = False)[0]
        off += shader.insert_multiple_lines(line + off + 1, '''
            // ProjectToPixelMatrix - stereo correction * resolution / 2:
            add {stereo}.w, {depth}, -{stereo}.y
            mul {stereo}.w, {stereo}.w, {stereo}.x
            mul {stereo}.w, {stereo}.w, {ViewportSize}.x
            mad {x}, {stereo}.w, l(0.5), {x}
        '''.format(
            stereo = shader.stereo_params_reg,
            depth = instr.lval,
            x = x_instr.lval,
            ViewportSize = ViewportSize,
        ))


    shader.autofixed = True

def fix_wd2_screen_space_reflections_cs(shader):
    try:
        SSPRWMirrorViewProjMatrix = cb_matrix(*shader.find_cb_entry('float4x4', 'SSPRWMirrorViewProjMatrix'))
    except KeyError:
        debug_verbose(0, 'Shader does not declare all required values for the WATCH_DOGS2 screen space reflection fix')
        return

    results = shader.scan_shader(SSPRWMirrorViewProjMatrix[3], write = False)
    if not results:
        debug_verbose(0, 'Shader does not use SSPRWMirrorViewProjMatrix for the WATCH_DOGS2 screen space reflection fix')
        return

    shader.insert_stereo_params()
    shader.early_insert_vanity_comment("WATCH_DOGS2 Screen Space Reflection fix (Compute Shader variant) inserted with")

    fix_wd2_unproject(shader, allow_multiple=True)

    try:
        fix_wd2_camera_pos(shader)
    except:
        # Not all shaders have this
        pass

    off = 0
    for line, instr in shader.scan_shader(SSPRWMirrorViewProjMatrix[3], write = False):
        x_line, x_instr = shader.scan_shader(SSPRWMirrorViewProjMatrix[0], start = line + off - 1, direction = -1, stop = True, write = False)[0]
        off += shader.insert_multiple_lines(line + off + 1, '''
            // SSPRWMirrorViewProjMatrix - subtract stereo correction:
            add {stereo}.w, {depth}, -{stereo}.y
            mad {x}, -{stereo}.w, {stereo}.x, {x}
        '''.format(
            stereo = shader.stereo_params_reg,
            depth = instr.lval,
            x = x_instr.lval,
        ))

    shader.autofixed = True

def fix_wd2_soft_shadows(shader):
    # Soft shadow shaders in WATCH_DOGS2 lack headers
    try:
        shader.find_header(resource_bindings_pattern)
        return
    except KeyError:
        # Missing headers, we can proceed
        pass

    inv_projection = cb_matrix(13, 36 * 16)

    try:
        results = shader.find_col_major_matrix_multiply(inv_projection)
    except KeyError:
        return

    if any([ r.instruction.lval.variable != results[0].instruction.lval.variable for r in results ]):
        debug_verbose(0, 'Matrix writing to differing output variables')
        raise KeyError()

    # Check matrix multiplication writes x, y, z, w in order. Results will
    # already be in order of constant value, so const index is implicitly
    # checked by the line order below
    if any([ r.instruction.lval.components != 'xyzw'[i] for (i, r) in enumerate(results) ]):
        debug_verbose(0, 'Matrix not writing to expected components')
        raise KeyError()

    line, instr = results[3]

    results = shader.scan_shader(instr.lval.variable, start = line + 1, write = False, stop = True, stop_when_clobbered = True, instr_type = DivInstruction)
    if not results or results[0].line != line + 1 or results[0].instruction.lval.components != 'xyzw':
        debug_verbose(0, 'Inverse projection matrix normalisation not in expected location')
        return
    line, instr = results[0]
    vpos = instr.lval.variable

    off = shader.insert_stereo_params()
    off += shader.insert_vanity_comment(line + off + 1, 'WATCH_DOGS2 soft shadows fix inserted with')
    off += shader.insert_multiple_lines(line + off + 1, '''
        add {stereo}.w, {vpos}.z, -{stereo}.y
        mul {stereo}.w, {stereo}.w, {stereo}.x
        mad {vpos}.x, -{stereo}.w, {inv_projection0}.x, {vpos}.x
    '''.format(
        stereo = shader.stereo_params_reg,
        inv_projection0 = inv_projection[0],
        vpos = vpos,
    ))

    shader.autofixed = True

def fix_wd2_lens_grit(shader, param):
    # Adjusts the lens grit depth by percentage of infinity passed in from an
    # ini param, but also stretches it to avoid clipping

    assert(len(param) == 2)
    param_idx = int(param[1])
    param_component = param[0]
    assert(param_component in 'xyzw')

    for name in ('HDRLighting__LensDirtTexture__TexObj__', 'HDRLighting__LensDirtTexture2__TexObj__'):
        try:
            tex = shader.find_texture(name, format='float4', dim='2d')
        except KeyError:
            debug_verbose(0, 'Shader does not declare %s' % name)
            continue

        results = shader.scan_shader(tex, write=False)
        assert(len(results) == 1)
        line, instr = results[0]

        texcoord = instr.rargs[0]
        repl_texcoord = shader.allocate_temp_reg()
        tmp = shader.allocate_temp_reg()
        shader.replace_rval_reg_on_line(line, texcoord.variable, repl_texcoord)

        off = shader.insert_stereo_params()
        off += shader.insert_ini_params(param_idx)
        off += shader.insert_vanity_comment(line + off, 'WATCH_DOGS2 lens grit adjustment inserted with')
        off += shader.insert_multiple_lines(line + off, '''
            mov {repl_texcoord}.xyzw, {texcoord}.xyzw
            mul {stereo}.w, {stereo}.x, {param_reg}.{param_component}
            eq {tmp}.x, {stereo}.z, l(1.0)
            if_nz {tmp}.x
              add {tmp}.x, {stereo}.w, l(1.0)
              add {tmp}.y, {repl_texcoord}.{texcoord_x}, l(-1.0)
              mad {repl_texcoord}.{texcoord_x}, {tmp}.x, {tmp}.y, l(1.0)
            else
              add {tmp}.x, l(1.0), -{stereo}.w
              mul {repl_texcoord}.{texcoord_x}, {repl_texcoord}.{texcoord_x}, {tmp}.x
            endif
        '''.format(
            stereo = shader.stereo_params_reg,
            param_reg = shader.ini_params_reg[param_idx],
            param_component = param_component,
            texcoord = texcoord.variable,
            texcoord_x = texcoord.components[0],
            repl_texcoord = repl_texcoord,
            tmp = tmp,
        ))

        off += shader.insert_multiple_lines(line + off + 1, '''
            eq {tmp}.x, {param_reg}.{param_component}, l(-1.0)
            if_nz {tmp}.x
              mov {result}, l(0.0, 0.0, 0.0, 0.0)
            endif
        '''.format(
            param_reg = shader.ini_params_reg[param_idx],
            param_component = param_component,
            result = instr.lval,
            tmp = tmp,
        ))

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
    parser.add_argument('--fix-unusual-halo-with-inconsistent-w-optimisation', action='store_true',
            help="Attempt to automatically fix a vertex shader for an unusual halo pattern seen in some Unity 5.4 games (Stranded Deep)")
    parser.add_argument('--remap-cb', action='append', nargs=2, type=int, default=[],
            help="Remap accesses of a given constant buffer to a structured buffer")
    parser.add_argument('--disable-driver-stereo-cb', nargs='?', type=int, const=12,
            help="Disable the driver stereo correction by defining the same constant buffer it uses")
    parser.add_argument('--fix-unity-lighting-ps', nargs='?', const='TEXCOORD3',
           help="Apply a correction to Unity lighting pixel shaders. NOTE: This is only one part of the Unity lighting fix - you also need the vertex shaders & d3dx.ini from my template!")
    parser.add_argument('--fix-unity-reflection', action='store_true',
            help="Correct the Unity camera position to fix certain cases of specular highlights, reflections and some fake transparent windows. Requires a valid MVP and _Object2World matrices copied from elsewhere")
    parser.add_argument('--fix-unity-frustum-world', action='store_true',
            help="Applies a world-space correction to _FrustumCornersWS. Requires a valid MVP and _Object2World matrices copied from elsewhere")
    parser.add_argument('--fix-fcprimal-reflection', action='store_true',
            help="Fix a reflection shader in Far Cry Primal")
    parser.add_argument('--fix-fcprimal-physical-lighting', action='store_true',
            help="Fix a physical lighting compute shader in Far Cry Primal")
    parser.add_argument('--fix-fcprimal-camera-pos', action='store_true',
            help="Fix reflections, specular highlights, etc. by adjusting the camera position in Far Cry Primal")
    parser.add_argument('--fix-fcprimal-volumetric-fog', action='store_true',
            help="Fix various volumetric fog shaders")
    parser.add_argument('--fix-fcprimal-light-pos', action='store_true',
            help="Fix light position, for volumetric fog around point lights (WARNING: this might break some cave light shaft shaders)")
    parser.add_argument('--fix-wd2-unproject', action='store_true',
            help="Fix lights, etc. in WATCH_DOGS2")
    parser.add_argument('--fix-wd2-camera-pos', action='store_true',
            help="Fix specular highlights in WATCH_DOGS2")
    parser.add_argument('--fix-wd2-camera-pos-limit', type=int,
            help="As above, but limits the number of times camera position will be replaced in a shader (for glass)")
    parser.add_argument('--fix-wd2-camera-pos-excluding', type=int,
            help="As above, but skips the first n times camera position will be replaced in a shader (for building fake interiors)")
    parser.add_argument('--fix-wd2-volumetric-fog', action='store_true',
            help="Fix various volumetric fog shaders in WATCH_DOGS2")
    parser.add_argument('--fix-wd2-view-dir-reconstruction', action='store_true',
            help="Fix volumetric fog around the sun/moon (WARNING: Do not apply to other volumetric fog shaders!)")
    parser.add_argument('--fix-wd2-camera-z-axis', type=int, choices=(-1, 1),
            help="Experimental alternate volumetric fog pattern for WATCH_DOGS2 (use in conjunction with the view direction fix)")
    parser.add_argument('--fix-wd2-screen-space-reflections', action='store_true',
            help="Fix screen space reflections and environmental reflections in WATCH_DOGS2")
    parser.add_argument('--fix-wd2-screen-space-reflections-cs', action='store_true',
            help="Compute shader variant of the screen space reflection fix for WATCH_DOGS2")
    parser.add_argument('--fix-wd2-soft-shadows', action='store_true',
            help="Fix soft shadow shaders (PCSS) used in WATCH_DOGS2")
    parser.add_argument('--fix-wd2-lens-grit',
            help="Adjust the lens grit depth in WD2. Pass in the ini param containing the depth")
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
    success = False
    for file in args.files:
        debug_verbose(-2, 'parsing %s...' % file)
        shader = ASMShader(file)

        try:
            if args.auto_fix_vertex_halo:
                hlsltool.auto_fix_vertex_halo(shader)
            if args.fix_unusual_halo_with_inconsistent_w_optimisation:
                fix_unusual_halo_with_inconsistent_w_optimisation(shader)
            if args.fix_unity_lighting_ps:
                fix_unity_lighting_ps(shader)
            if args.fix_unity_reflection:
                fix_unity_reflection(shader)
            if args.fix_unity_frustum_world:
                fix_unity_frustum_world(shader)
            if args.fix_fcprimal_reflection:
                fix_fcprimal_reflection(shader)
            if args.fix_fcprimal_physical_lighting:
                fix_fcprimal_physical_lighting(shader)
            if args.fix_fcprimal_camera_pos:
                fix_fcprimal_camera_pos(shader)
            if args.fix_fcprimal_volumetric_fog:
                fix_fcprimal_volumetric_fog(shader)
            if args.fix_wd2_volumetric_fog:
                fix_wd2_volumetric_fog(shader)
            if args.fix_wd2_view_dir_reconstruction:
                fix_wd2_view_dir_reconstruction(shader)
            if args.fix_wd2_camera_z_axis:
                fix_wd2_camera_z_axis(shader, args.fix_wd2_camera_z_axis)
            if args.fix_fcprimal_light_pos:
                fix_fcprimal_light_pos(shader)
            if args.fix_wd2_screen_space_reflections:
                fix_wd2_screen_space_reflections(shader)
            if args.fix_wd2_screen_space_reflections_cs:
                fix_wd2_screen_space_reflections_cs(shader)
            if args.fix_wd2_unproject:
                fix_wd2_unproject(shader)
            if args.fix_wd2_camera_pos_limit or args.fix_wd2_camera_pos_excluding:
                fix_wd2_camera_pos(shader, limit = args.fix_wd2_camera_pos_limit, exclude = args.fix_wd2_camera_pos_excluding)
            elif args.fix_wd2_camera_pos:
                fix_wd2_camera_pos(shader)
            if args.fix_wd2_soft_shadows:
                fix_wd2_soft_shadows(shader)
            if args.fix_wd2_lens_grit:
                fix_wd2_lens_grit(shader, args.fix_wd2_lens_grit)
            for cb, sb in args.remap_cb:
                # Do this late in case it is used in conjunction with other patterns
                remap_cb(shader, cb, sb)
            if args.disable_driver_stereo_cb is not None:
                disable_driver_stereo_cb(shader)
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
                success = True
            if args.in_place:
                tmp = '%s.new' % real_file
                print(shader, end='', file=open(tmp, 'w'))
                os.rename(tmp, real_file)
                shader.update_ini()
                success = True
            if args.install:
                if hlsltool.install_shader(shader, file, args):
                    shader.update_ini()
                    success = True
            if args.install_to:
                if hlsltool.install_shader_to(shader, file, args, os.path.expanduser(args.install_to), True):
                    shader.update_ini()
                    success = True
            if args.to_git:
                a = copy.copy(args)
                a.force = True
                if hlsltool.install_shader_to_git(shader, file, a):
                    shader.update_ini()
                    success = True
    show_collected_errors()
    hlsltool.do_ini_updates()
    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()

# vi: et ts=4:sw=4
