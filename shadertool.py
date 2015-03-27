#!/usr/bin/env python3

import sys, os, re, argparse, json, itertools, glob, shutil, copy, collections

import shaderutil

preferred_stereo_const = 220
dx9settings_ini = {}

reg_names = {
    'c': 'Referenced Constants',
    'r': 'Temporary',
    's': 'Samplers',
    'v': 'Inputs',
    'o': 'Outputs',
    'oC': 'Output Colour',
    'oPos': 'Output Position (shader model < 3)',
    'oT': 'Output Texcoord (shader model < 3)',
    'oD': 'Output Colour (shader model < 3)',
    'oFog': 'Output Fog (shader model < 3)',
    'oPts': 'Output Point Size Register (shader model < 3)',
    't': 'Input Texcoord (shader model < 3)',
}

class NoFreeRegisters(Exception): pass

verbosity = 0
def debug(*args, **kwargs):
    print(file=sys.stderr, *args, **kwargs)

def debug_verbose(level, *args, **kwargs):
    if verbosity >= level:
        return debug(*args, **kwargs)

class InstructionSeparator(object): pass # Newline and semicolon
class Ignore(object): pass # Tokens ignored when analysing shader, but preserved for manipulation (whitespace, comments)
class Strip(object): pass # Removed during tokenisation, not preserved
class Number(object): pass

class Token(str):
    def __new__(cls, string):
        match = cls.pattern.match(string)
        if match is None:
            return None
        ret = str.__new__(cls, match.string[:match.end()])
        return ret

# class Minus(Token):
#     pattern = re.compile(r'-')

class Identifier(Token):
    pattern = re.compile(r'[a-zA-Z_\-!][a-zA-Z_0-9\.]*(\[a0(\.[abcdxyzw]{1,4})?(\s*\+\s*\d+)?\](\.[abcdxyzw]{1,4})?)?')

class Comma(Token):
    pattern = re.compile(r',')

class Float(Token, Number):
    pattern = re.compile(r'-?[0-9]*\.[0-9]*(e[-+]?[0-9]+)?')

class Int(Token, Number):
    pattern = re.compile(r'-?[0-9]+')

class CPPStyleComment(Token, Ignore):
    pattern = re.compile(r'\/\/.*$', re.MULTILINE)

class SemiColonComment(Token, Ignore):
    pattern = re.compile(r';.*$', re.MULTILINE)

class HashComment(Token, Ignore):
    pattern = re.compile(r'#.*$', re.MULTILINE)

class CStyleComment(Token, Ignore): # XXX: Are these valid in shader asm language?
    pattern = re.compile(r'\/\*.*\*\/', re.MULTILINE)

class WhiteSpace(Token, Ignore):
    pattern = re.compile(r'[ \t]+')

class NewLine(WhiteSpace, InstructionSeparator):
    pattern = re.compile(r'\n')

class NullByte(Token, Strip):
    pattern = re.compile(r'\0')

    def __str__(self):
        return ''

class Bracket(Token):
    pattern = re.compile(r'(\(|\))') # Seen in a Miasmata preshader

class Anything(Token):
    pattern = re.compile(r'.')

tokens = (
    CPPStyleComment,
    SemiColonComment, # Seen in declaration section of shaders extracted from Unity like '; 52 ALU, 5 TEX'
    HashComment, # Seen in Stacking with installation path & line numbers
    CStyleComment, # XXX: Are these valid in shader asm?
    NewLine,
    WhiteSpace,
    Comma,
    Float,
    Int,
    # Minus,
    Identifier,
    Bracket,
    NullByte,
    # Anything,
)

def parse_token(shader):
    for t in tokens:
        token = t(shader)
        if token is not None:
            return (token, shader[len(token):])
    try:
        msg = shader.split('\n')[0]
    except:
        msg = shader
    raise SyntaxError(msg)

def tokenise(shader):
    result = []
    while shader:
        (token, shader) = parse_token(shader)
        if not isinstance(token, Strip):
            result.append(token)
    return result

class SyntaxTree(list):
    def __repr__(self):
        return '[%s]' % '|'.join([ {True: repr(t), False: str(t)}[isinstance(t, SyntaxTree)] for t in self ])

    def __str__(self):
        return ''.join(map(str, self))

    def iter_all(self):
        '''
        Walk tree returning both tree and leaf nodes. Parent and index is also
        returned for each node to allow for easy replacing.
        '''
        for (i, token) in enumerate(self):
            yield (token, self, i)
            if isinstance(token, SyntaxTree):
                for (j, (t, p, pi)) in enumerate(token.iter_all()):
                    yield (t, p, pi)

    def iter_flat(self):
        '''
        Walk tree returning only leaf nodes
        '''
        for token in self:
            if isinstance(token, SyntaxTree):
                for t in token:
                    yield t
            else:
                yield token

    @staticmethod
    def split_newlines(old_tree): # Also splits on semicolons (untested)
        tree = SyntaxTree([])
        t = SyntaxTree([])
        for token in old_tree:
            if isinstance(token, InstructionSeparator):
                if t:
                    tree.append(t)
                    t = SyntaxTree([])
                tree.append(token)
            else:
                t.append(token)
        if t:
            tree.append(t)
        return tree


class Preshader(SyntaxTree):
    def __init__(self, lst):
        newlst = []
        for line in lst:
            if isinstance(line, Ignore):
                newlst.append(line)
                continue
            for token in line:
                if not isinstance(token, Ignore):
                    newlst.append(CPPStyleComment('//PRESHADER %s' % str(line)))
                    break
            else:
                newlst.append(line)
        SyntaxTree.__init__(self, newlst)

class OpCode(str):
    pass

class Register(str):
    pattern = re.compile(r'''
        (?P<negate>-)?
        (?P<not>!)?
        (?P<type>[a-zA-Z]+)
        (?P<num>\d*)
        (?P<absolute>_abs)?
        (?P<address_reg>
            \[a0
                (?:\.[abcdxyzw]{1,4})?
                (?:\s*\+\s*\d+)?
            \]
        )?
        (?:
            \.
            (?P<swizzle>[abcdxyzw]{1,4})
        )?
        $
    ''', re.VERBOSE)
    def __new__(cls, s):
        match = cls.pattern.match(s)
        if match is None:
            raise SyntaxError('Expected register, found %s' % s)
        ret = str.__new__(cls, s)
        ret.negate = match.group('negate') or ''
        ret.bool_not = match.group('not') or ''
        ret.absolute = match.group('absolute') or ''
        ret.type = match.group('type')
        ret.num = match.group('num')
        ret.reg = ret.type + ret.num # FIXME: Turn into property
        ret.address_reg = match.group('address_reg')
        if ret.num:
            ret.num = int(ret.num)
        ret.swizzle = match.group('swizzle')
        return ret

    def __lt__(self, other):
        if isinstance(self.num, int) and isinstance(other.num, int):
            return self.num < other.num
        return str.__lt__(self, other)

    def __str__(self, negate=None):
        if negate is None:
            negate = self.negate
        r = '%s%s%s%s' % (negate, self.bool_not, self.reg, self.absolute) # FIXME: Sync type and num if reg changed
        if self.address_reg:
            r += self.address_reg
        if self.swizzle:
            r += '.%s' % self.swizzle
        return r

    def __neg__(self):
        if self.negate:
            negate = ''
        else:
            negate = '-'
        return Register(self.__str__(negate))

    # TODO: use __get_attr__ to handle all permutations of this:
    @property
    def x(self): return Register('%s.x' % (self.reg))
    @property
    def y(self): return Register('%s.y' % (self.reg))
    @property
    def z(self): return Register('%s.z' % (self.reg))
    @property
    def w(self): return Register('%s.w' % (self.reg))
    @property
    def xxxx(self): return Register('%s.xxxx' % (self.reg))
    @property
    def yyyy(self): return Register('%s.yyyy' % (self.reg))

class Instruction(SyntaxTree):
    def is_declaration(self):
        return self.opcode.startswith('dcl_') or self.opcode == 'dcl'

    def is_definition(self):
        return self.opcode == 'def' or self.opcode == 'defi'

    def is_def_or_dcl(self):
        return self.is_definition() or self.is_declaration() or self.opcode in sections

class NewInstruction(Instruction):
    def __init__(self, opcode, args):
        self.opcode = OpCode(opcode)
        self.args = args
        tree = [self.opcode]
        if args:
            tree.append(WhiteSpace(' '))
            for arg in args[:-1]:
                tree.append(arg)
                tree.append(Comma(','))
                tree.append(WhiteSpace(' '))
            tree.append(args[-1])
        Instruction.__init__(self, tree)

def parse_instruction(line):
    tree = Instruction([])
    tree.opcode = OpCode(line.pop(0))
    tree.args = []
    tree.append(tree.opcode)
    expect = Register
    while (line):
        if all([ isinstance(t, Ignore) for t in line ]):
            break
        token = line.pop(0)
        if isinstance(token, Ignore):
            pass
        # elif isinstance(token, Minus):
        #     if expect != Register and expect != Number:
        #         raise SyntaxError("Expected %s, found %s" % (expect.__name__, token))
        elif isinstance(token, Identifier):
            if expect != Register:
                raise SyntaxError("Expected %s, found %s" % (expect.__name__, token))
            token = Register(token)
            tree.args.append(token)
            expect = Comma
            if tree.is_declaration():
                expect = type(None)
        elif isinstance(token, Number):
            if expect != Number:
                raise SyntaxError("Expected %s, found %s" % (expect.__name__, token))
            tree.args.append(token)
            expect = Comma
        elif isinstance(token, Comma):
            if expect != Comma:
                raise SyntaxError("Expected %s, found %s" % (expect.__name__, token))
            expect = Register
            if tree.is_definition():
                expect = Number
        else:
            raise SyntaxError("Unexpected token: %s" % token)
        tree.append(token)
    return tree

class RegSet(set):
    '''
    Discards swizzle, negate and absolute value modifiers to considder register uniqueness
    '''
    def add(self, reg):
        set.add(self, Register(reg.reg))

class ShaderBlock(SyntaxTree):
    def __init__(self, tree, shader_start):
        newtree = []
        if shader_start is not None:
            self.shader_start = shader_start
            self.decl_end = next_line_pos(self, shader_start)
        in_dcl = True
        for (lineno, line) in enumerate(tree):
            if isinstance(line, Ignore):
                newtree.append(line)
                continue
            t = SyntaxTree([])
            while (line):
                if isinstance(line[0], Ignore):
                    t.append(line.pop(0))
                    continue
                inst = parse_instruction(line)
                if inst.is_def_or_dcl():
                    if not in_dcl:
                        raise SyntaxError("Bad shader: Mixed declarations with code: %s" % inst)
                elif in_dcl:
                    self.decl_end = lineno
                    in_dcl = False
                t.append(inst)
            newtree.append(t)
        SyntaxTree.__init__(self, newtree)

    def insert_decl(self, *inst, comment=None):
        off = 1
        line = SyntaxTree()
        if inst:
            line.append(NewInstruction(*inst))
        if inst and comment:
            line.append(WhiteSpace(' '))
        if comment:
            line.append(CPPStyleComment('// %s' % comment))
        if line:
            self.insert(self.decl_end, line)
            self.decl_end += 1
            off += 1
        self.insert(self.decl_end, NewLine('\n'))
        self.decl_end += 1
        return off

    def insert_instr(self, pos, inst=None, comment=None):
        self.insert(pos, NewLine('\n'))
        line = SyntaxTree()
        if inst:
            line.append(inst)
        if inst and comment:
            line.append(WhiteSpace(' '))
        if comment:
            line.append(CPPStyleComment('// %s' % comment))
        if line:
            self.insert(pos, line)
            return 2
        return 1

    def add_inst(self, *inst):
        if inst:
            self.append(SyntaxTree([NewInstruction(*inst)]))
        self.append(NewLine('\n'))

    def analyse_regs(self, verbose=False):
        def pr_verbose(*args, **kwargs):
            if verbose:
                debug(*args, **kwargs)
        self.local_consts = RegSet()
        self.addressed_regs = RegSet()
        self.declared = []
        self.reg_types = {}
        for (inst, parent, idx) in self.iter_all():
            if not isinstance(inst, Instruction):
                continue
            if inst.is_definition():
                self.local_consts.add(inst.args[0])
                continue
            if inst.is_declaration():
                self.declared.append((inst.opcode, inst.args[0]))
                continue
            for arg in inst.args:
                if arg.type not in self.reg_types:
                    self.reg_types[arg.type] = RegSet()
                self.reg_types[arg.type].add(arg)
                if arg.address_reg:
                    self.addressed_regs.add(arg)

        self.global_consts = self.unref_consts = self.consts = RegSet()
        if 'c' in self.reg_types:
            self.consts = self.reg_types['c']
            self.global_consts = self.consts.difference(self.local_consts)
            self.unref_consts = self.local_consts.difference(self.consts)

        pr_verbose('Local constants: %s' % ', '.join(sorted(self.local_consts)))
        pr_verbose('Global constants: %s' % ', '.join(sorted(self.global_consts)))
        pr_verbose('Unused local constants: %s' % ', '.join(sorted(self.unref_consts)))
        pr_verbose('Declared: %s' % ', '.join(['%s %s' % (k, v) \
                for (k, v) in sorted(self.declared)]))
        for (k, v) in self.reg_types.items():
            pr_verbose('%s: %s' % (reg_names.get(k, k), ', '.join(sorted(v))))

    def _find_free_reg(self, reg_type, model, desired=0):
        if reg_type not in self.reg_types:
            r = Register(reg_type + str(desired))
            self.reg_types[reg_type] = RegSet([r])
            return r

        if model is None:
            model = type(self)

        # Treat all defined constants as taken, even if they aren't used (if we
        # were ever really tight on space we could discard unused local
        # constants):
        taken = self.reg_types[reg_type].union(self.local_consts)
        for num in [desired] + list(range(model.max_regs[reg_type])):
            reg = reg_type + str(num)
            if reg not in taken:
                r = Register(reg)
                self.reg_types[reg_type].add(r)
                return r

        raise NoFreeRegisters(self.filename, reg_type)

    def do_replacements(self, regs, replace_dcl, insts=None, callbacks=None):
        for (node, parent, idx) in self.iter_all():
            if isinstance(node, Register):
                if not replace_dcl and parent.is_declaration():
                    continue
                if regs is not None and node.reg in regs:
                    node.reg = regs[node.reg] # FIXME: Update reg.type
            if isinstance(node, Instruction):
                if insts is not None and node.opcode in insts:
                    parent[idx] = insts[node.opcode]
                if callbacks is not None and node.opcode in callbacks:
                    callbacks[node.opcode](self, node, parent, idx)

    def discard_if_unused(self, regs, reason = 'unused'):
        self.analyse_regs()
        discard = self.unref_consts.intersection(RegSet(regs))
        if not discard:
            return
        for (node, parent, idx) in self.iter_all():
            if isinstance(node, Instruction) and node.is_definition() and node.args[0] in discard:
                parent[idx] = CPPStyleComment('// Discarded %s constant %s' % (reason, node.args[0]))

def fixup_sincos(tree, node, parent, idx):
    parent[idx] = NewInstruction('sincos', (node.args[0], node.args[1]))
    tree.discard_if_unused((node.args[2], node.args[3]), 'sincos')

def fixup_mova(tree, node, parent, idx):
    if node.args[0].reg == 'a0':
        parent[idx] = NewInstruction('mova', (node.args[0], node.args[1]))

class VertexShader(ShaderBlock): pass
class PixelShader(ShaderBlock): pass

class VS3(VertexShader):
    max_regs = { # http://msdn.microsoft.com/en-us/library/windows/desktop/bb172963(v=vs.85).aspx
        'c': 256,
        'i': 16,
        'o': 12,
        'r': 32,
        's': 4,
        'v': 16,
    }
    def_stereo_sampler = 's0'

class PS3(PixelShader):
    max_regs = { # http://msdn.microsoft.com/en-us/library/windows/desktop/bb172920(v=vs.85).aspx
        'c': 224,
        'i': 16,
        'r': 32,
        's': 16,
        'v': 12,
    }
    def_stereo_sampler = 's13'

def vs_to_shader_model_3_common(shader, shader_model, args, extra_fixups = {}):
    shader.analyse_regs()
    shader.insert_decl()
    replace_regs = {}

    if 'oT' in shader.reg_types:
        for reg in sorted(shader.reg_types['oT']):
            opcode = 'dcl_texcoord'
            if reg.num:
                opcode = 'dcl_texcoord%d' % reg.num
            out = shader._find_free_reg('o', VS3)
            shader.insert_decl(opcode, [out])
            replace_regs[reg.reg] = out

    if 'oPos' in shader.reg_types:
        out = shader._find_free_reg('o', VS3)
        shader.insert_decl('dcl_position', [out])
        replace_regs['oPos'] = out


    if 'oD' in shader.reg_types:
        for reg in sorted(shader.reg_types['oD']):
            opcode = 'dcl_color'
            if reg.num:
                opcode = 'dcl_color%d' % reg.num
            out = shader._find_free_reg('o', VS3)
            shader.insert_decl(opcode, [out])
            replace_regs[reg.reg] = out

    if 'oFog' in shader.reg_types:
        out = shader._find_free_reg('o', VS3)
        shader.insert_decl('dcl_fog', [out])
        replace_regs['oFog'] = out
    if 'oPts' in shader.reg_types:
        out = shader._find_free_reg('o', VS3)
        shader.insert_decl('dcl_psize', [out])
        replace_regs['oPts'] = out

    shader.insert_decl()

    fixups = {'sincos': fixup_sincos}
    fixups.update(extra_fixups)

    shader.do_replacements(replace_regs, True, {shader_model: 'vs_3_0'}, fixups)

    shader.__class__ = VS3

    if (args.add_fog_on_sm3_update):
        shader.analyse_regs()
        add_unity_autofog_VS3(shader, reason="for fog compatibility on upgrade from %s to vs_3_0" % shader_model)

def insert_converted_by(tree, orig_model):
    pos = prev_line_pos(tree, tree.shader_start)
    tree[tree.shader_start].append(WhiteSpace(' '))
    tree[tree.shader_start].append(CPPStyleComment("// Converted from %s with DarkStarSword's shadertool.py" % orig_model))

class VS11(VertexShader):
    def to_shader_model_3(self, args):
        # NOTE: Only very lightly tested!
        vs_to_shader_model_3_common(self, 'vs_1_1', args, {'mov': fixup_mova})
        insert_converted_by(self, 'vs_1_1')

class VS2(VertexShader):
    def to_shader_model_3(self, args):
        vs_to_shader_model_3_common(self, 'vs_2_0', args)
        insert_converted_by(self, 'vs_2_0')

class PS2(PixelShader):
    model = 'ps_2_0'

    def to_shader_model_3(self, args):
        def fixup_ps2_dcl(tree, node, parent, idx):
            modifier = node.opcode[3:]
            reg = node.args[0]
            if reg.type == 'v':
                node.opcode = 'dcl_color%s' % modifier
                if reg.num:
                    node.opcode = 'dcl_color%d%s' % (reg.num, modifier)
            elif reg.type == 't':
                node.opcode = 'dcl_texcoord%s' % modifier
                if reg.num:
                    node.opcode = 'dcl_texcoord%d%s' % (reg.num, modifier)
            node[0] = node.opcode
        self.analyse_regs()
        replace_regs = {}

        if 't' in self.reg_types:
            for reg in sorted(self.reg_types['t']):
                replace_regs[reg.reg] = new_reg = self._find_free_reg('v', PS3)

        self.do_replacements(replace_regs, True, {self.model: 'ps_3_0'},
                {'sincos': fixup_sincos, 'dcl': fixup_ps2_dcl,
                'dcl_centroid': fixup_ps2_dcl, 'dcl_pp': fixup_ps2_dcl})
        insert_converted_by(self, self.model) # Do this before changing the class!
        self.__class__ = PS3

class PS2X(PS2):
    # Need to verify, but this looks like the same conversion as ps_2_0 should
    # work
    model = 'ps_2_x'

sections = {
    'vs_3_0': VS3,
    'ps_3_0': PS3,
    'vs_2_0': VS2,
    'ps_2_0': PS2,
    'ps_2_x': PS2X,
    'vs_1_1': VS11,
}

def process_sections(tree):
    '''
    Preshader will be commented out, main shader will by analysed and turned
    into a series of instructions
    '''
    preshader_start = None
    for (lineno, line) in enumerate(tree):
        if not isinstance(line, SyntaxTree):
            continue
        for token in line:
            if isinstance(token, Ignore):
                continue
            if token == 'preshader':
                if preshader_start is not None:
                    raise SyntaxError('Multiple preshader blocks')
                preshader_start = lineno
                # debug('Preshader found starting on line %i' % lineno)
            elif token in sections:
                # debug('Identified shader type %s' % token)
                head = SyntaxTree(tree[:lineno])
                preshader = SyntaxTree([])
                if preshader_start is not None:
                    head = SyntaxTree(tree[:preshader_start])
                    preshader = Preshader(tree[preshader_start:lineno])
                return sections[token](head + preshader + tree[lineno:], lineno)
            elif preshader_start is None:
                raise SyntaxError('Unexpected token while searching for shader type: %s' % token)
    raise SyntaxError('Unable to identify shader type')

def parse_shader(shader, args = None):
    tokens = tokenise(shader)
    if args and args.debug_tokeniser:
        for token in tokens:
            debug('%s: %s' % (token.__class__.__name__, repr(str(token))))
    tree = SyntaxTree(tokens)
    tree = SyntaxTree.split_newlines(tree)
    tree = process_sections(tree)
    return tree

def install_shader_to(shader, file, args, base_dir, show_full_path=False):
    try:
        os.mkdir(base_dir)
    except OSError:
        pass

    override_dir = os.path.join(base_dir, 'ShaderOverride')
    try:
        os.mkdir(override_dir)
    except OSError:
        pass

    if isinstance(shader, VertexShader):
        shader_dir = os.path.join(override_dir, 'VertexShaders')
    elif isinstance(shader, PixelShader):
        shader_dir = os.path.join(override_dir, 'PixelShaders')
    else:
        raise Exception("Unrecognised shader type: %s" % shader.__class__.__name__)
    try:
        os.mkdir(shader_dir)
    except OSError:
        pass

    dest_name = '%s.txt' % shaderutil.get_filename_crc(file)
    dest = os.path.join(shader_dir, dest_name)
    if not args.force and os.path.exists(dest):
        debug_verbose(0, 'Skipping %s - already installed' % file)
        return False

    if show_full_path:
        debug_verbose(0, 'Installing to %s...' % dest)
    else:
        debug_verbose(0, 'Installing to %s...' % os.path.relpath(dest, os.curdir))
    print(shader, end='', file=open(dest, 'w'))

    return True # Returning success will allow ini updates

def install_shader(shader, file, args):
    if not (isinstance(shader, (VS3, PS3))):
        raise Exception("Shader must be a vs_3_0 or a ps_3_0, but it's a %s" % shader.__class__.__name__)

    src_dir = os.path.dirname(os.path.join(os.curdir, file))
    dumps = os.path.realpath(os.path.join(src_dir, '../..'))
    if os.path.basename(dumps).lower() != 'dumps':
        raise Exception("Not installing %s - not in a Dumps directory" % file)
    gamedir = os.path.realpath(os.path.join(src_dir, '../../..'))

    return install_shader_to(shader, file, args, gamedir)

def check_shader_installed(file):
    # TODO: Refactor common code with install functions
    src_dir = os.path.realpath(os.path.dirname(os.path.join(os.curdir, file)))
    dumps = os.path.realpath(os.path.join(src_dir, '../..'))
    if os.path.basename(dumps).lower() != 'dumps':
        raise Exception("Not checking if %s installed - not in a Dumps directory" % file)
    gamedir = os.path.realpath(os.path.join(src_dir, '../../..'))

    override_dir = os.path.join(gamedir, 'ShaderOverride')

    if os.path.basename(src_dir).lower().startswith('vertex'):
        shader_dir = os.path.join(override_dir, 'VertexShaders')
    elif os.path.basename(src_dir).lower().startswith('pixel'):
        shader_dir = os.path.join(override_dir, 'PixelShaders')
    else:
        raise ValueError("Couldn't determine type of shader from directory")

    dest_name = '%s.txt' % shaderutil.get_filename_crc(file)
    dest = os.path.join(shader_dir, dest_name)
    return os.path.exists(dest)

def find_game_dir(file):
    src_dir = os.path.dirname(os.path.join(os.curdir, file))
    parent = os.path.realpath(os.path.join(src_dir, '..'))
    if os.path.basename(parent).lower() == 'shaderoverride':
        return os.path.realpath(os.path.join(parent, '..'))
    parent = os.path.realpath(os.path.join(parent, '..'))
    if os.path.basename(parent).lower() != 'dumps':
        raise ValueError('Unable to find game directory')
    return os.path.realpath(os.path.join(parent, '..'))

def get_alias(game):
    try:
        with open(os.path.join(os.path.dirname(__file__), '.aliases.json'), 'r', encoding='utf-8') as f:
            aliases = json.load(f)
            return aliases.get(game, game)
    except IOError:
        return game

def install_shader_to_git(shader, file, args):
    game_dir = find_game_dir(file)

    # Filter out common subdirectory names:
    blacklisted_names = ('win32', 'win64', 'binaries')
    while os.path.basename(game_dir).lower() in blacklisted_names:
        game_dir = os.path.realpath(os.path.join(game_dir, '..'))

    game = os.path.basename(game_dir)
    script_dir = os.path.dirname(__file__)
    alias = get_alias(game)
    dest_dir = os.path.join(script_dir, alias)

    return install_shader_to(shader, file, args, dest_dir, True)

def find_original_shader(file):
    game_dir = find_game_dir(file)
    crc = shaderutil.get_filename_crc(file)
    src_dir = os.path.realpath(os.path.dirname(os.path.join(os.curdir, file)))
    if os.path.basename(src_dir).lower().startswith('vertex'):
        pattern = 'Dumps/AllShaders/VertexShader/%s.txt' % crc
    elif os.path.basename(src_dir).lower().startswith('pixel'):
        pattern = 'Dumps/AllShaders/PixelShader/CRC32_%s_*.txt' % (crc.lstrip('0'))
    else:
        raise ValueError("Couldn't determine type of shader from directory")
    pattern = os.path.join(game_dir, pattern)
    files = glob.glob(pattern)
    if not files:
        raise OSError('Unable to find original shader for %s: %s not found' % (file, pattern))
    return files[0]

def restore_original_shader(file):
    try:
        shutil.copyfile(find_original_shader(file), file)
    except OSError as e:
        debug(str(e))

def insert_stereo_declarations(tree, args, x=0, y=1, z=0.0625, w=0.5):
    if hasattr(tree, 'stereo_const'):
        return tree.stereo_const, 0

    if isinstance(tree, VertexShader) and args.stereo_sampler_vs:
        tree.stereo_sampler = args.stereo_sampler_vs
    elif isinstance(tree, PixelShader) and args.stereo_sampler_ps:
        tree.stereo_sampler = args.stereo_sampler_ps
    elif 's' in tree.reg_types and tree.def_stereo_sampler in tree.reg_types['s']:
        # FIXME: There could be a few reasons for this. For now I assume the
        # shader was already using the sampler, but it's also possible we have
        # simply already added the stereo texture.

        tree.stereo_sampler = tree._find_free_reg('s', None)
        debug('WARNING: SHADER ALREADY USES %s! USING %s FOR STEREO SAMPLER INSTEAD!' % \
                (tree.def_stereo_sampler, tree.stereo_sampler))

        if isinstance(tree, VertexShader):
            acronym = 'VS'
            quirk = 257
        elif isinstance(tree, PixelShader):
            acronym = 'PS'
            quirk = 0
        else:
            raise AssertionError()

        if not hasattr(tree, 'ini'):
            tree.ini = []
        tree.ini.append(('Def%sSampler' % acronym,
            str(quirk + tree.stereo_sampler.num),
            'Shader already uses %s, so use %s instead:' % \
                (tree.def_stereo_sampler, tree.stereo_sampler)
            ))
    else:
        tree.stereo_sampler = tree.def_stereo_sampler

    if args.adjust_multiply and args.adjust_multiply != -1:
        w = args.adjust_multiply
    tree.stereo_const = tree._find_free_reg('c', None, desired = preferred_stereo_const)
    offset = 0
    offset += tree.insert_decl()
    offset += tree.insert_decl('def', [tree.stereo_const, x, y, z, w])
    offset += tree.insert_decl('dcl_2d', [tree.stereo_sampler])
    offset += tree.insert_decl()
    return tree.stereo_const, offset

vanity_args = None
def vanity_comment(args, tree, what):
    global vanity_args

    if vanity_args is None:
        # Using a set here for *MASSIVE* performance boost over a list (e.g.
        # Life Is Strange has 75,000 pixel shaders hangs for minutes as a list,
        # as a set it's a fraction of a second)
        file_set = set(args.files)
        vanity_args = list(filter(lambda x: x not in file_set, sys.argv[1:]))

    return [
        "%s DarkStarSword's shadertool.py:" % what,
        '%s %s' % (os.path.basename(sys.argv[0]), ' '.join(vanity_args + [tree.filename])),
    ]

def insert_vanity_comment(args, tree, where, what):
    off = 0
    off += tree.insert_instr(where + off)
    for comment in vanity_comment(args, tree, what):
        off += tree.insert_instr(where + off, comment = comment)
    return off

def append_vanity_comment(args, tree, what):
    tree.add_inst()
    for comment in vanity_comment(args, tree, what):
        tree.append(CPPStyleComment('// %s' % comment))
        tree.append(NewLine('\n'))

def output_texcoords(tree):
    for (t, r) in tree.declared:
        if t.startswith('dcl_texcoord') and r.startswith('o'):
            yield (t, r)

def find_declaration(tree, type, prefix = None):
    for (t, r) in tree.declared:
        if t == type:
            if prefix and not r.startswith(prefix):
                continue
            return r
    raise IndexError()

def adjust_ui_depth(tree, args):
    if not isinstance(tree, VS3):
        raise Exception('UI Depth adjustment must be done on a vertex shader')

    stereo_const, _ = insert_stereo_declarations(tree, args)

    pos_reg = tree._find_free_reg('r', VS3)
    tmp_reg = tree._find_free_reg('r', VS3)
    dst_reg = find_declaration(tree, 'dcl_position', 'o').reg

    replace_regs = {dst_reg: pos_reg}
    tree.do_replacements(replace_regs, False)

    append_vanity_comment(args, tree, 'UI depth adjustment inserted with')
    if args.condition:
        tree.add_inst('mov', [tmp_reg.x, args.condition])
        tree.add_inst('if_eq', [tmp_reg.x, stereo_const.x])
    tree.add_inst('texldl', [tmp_reg, stereo_const.z, tree.stereo_sampler])
    separation = tmp_reg.x
    tree.add_inst('mad', [pos_reg.x, separation, args.adjust_ui_depth, pos_reg.x])
    if args.condition:
        tree.add_inst('endif', [])
    tree.add_inst('mov', [dst_reg, pos_reg])

def _adjust_output(tree, reg, args, stereo_const, tmp_reg):
    pos_reg = tree._find_free_reg('r', VS3)

    if reg.startswith('dcl_texcoord'):
        dst_reg = find_declaration(tree, reg, 'o').reg
    if reg.startswith('texcoord') or reg == 'position':
        dst_reg = find_declaration(tree, 'dcl_%s' % reg, 'o').reg
    else:
        dst_reg = reg
    replace_regs = {dst_reg: pos_reg}
    tree.do_replacements(replace_regs, False)

    append_vanity_comment(args, tree, 'Output adjustment inserted with')
    if args.condition:
        tree.add_inst('mov', [tmp_reg.x, args.condition])
        tree.add_inst('if_eq', [tmp_reg.x, stereo_const.x])
    tree.add_inst('texldl', [tmp_reg, stereo_const.z, tree.stereo_sampler])
    separation = tmp_reg.x; convergence = tmp_reg.y
    tree.add_inst('add', [tmp_reg.w, pos_reg.w, -convergence])
    if args.use_mad and not args.adjust_multiply:
        tree.add_inst('mad', [pos_reg.x, tmp_reg.w, separation, pos_reg.x])
    else:
        tree.add_inst('mul', [tmp_reg.w, tmp_reg.w, separation])
        if args.adjust_multiply and args.adjust_multiply != -1:
            tree.add_inst('mul', [tmp_reg.w, tmp_reg.w, stereo_const.w])
        if args.adjust_multiply and args.adjust_multiply == -1:
            tree.add_inst('add', [pos_reg.x, pos_reg.x, -tmp_reg.w])
        else:
            tree.add_inst('add', [pos_reg.x, pos_reg.x, tmp_reg.w])
    if args.condition:
        tree.add_inst('endif', [])
    tree.add_inst('mov', [dst_reg, pos_reg])

def adjust_output(tree, args):
    if not isinstance(tree, VS3):
        raise Exception('Output adjustment must be done on a vertex shader (currently)')

    stereo_const, _ = insert_stereo_declarations(tree, args)

    tmp_reg = tree._find_free_reg('r', VS3)

    for reg in args.adjust:
        _adjust_output(tree, reg, args, stereo_const, tmp_reg)

def auto_adjust_texcoords(tree, args):
    if not isinstance(tree, VS3):
        raise Exception('Auto texcoord adjustment is only applicable to vertex shaders')

    stereo_const, _ = insert_stereo_declarations(tree, args)
    pos_out = find_declaration(tree, 'dcl_position', 'o')
    pos_reg = tree._find_free_reg('r', VS3)
    pos_adj = tree._find_free_reg('r', VS3)
    tmp_reg = tree._find_free_reg('r', VS3)

    replace_regs = {pos_out: pos_reg}
    for (t, r) in output_texcoords(tree):
        replace_regs[r] = tree._find_free_reg('r', VS3)
    tree.do_replacements(replace_regs, False)

    append_vanity_comment(args, tree, 'Automatically adjust texcoords that match the output position. Inserted with')
    tree.add_inst('mov', [pos_out, pos_reg])
    for (t, r) in output_texcoords(tree):
        tree.add_inst('mov', [r, replace_regs[r]])
    if args.condition:
        tree.add_inst('mov', [tmp_reg.x, args.condition])
        tree.add_inst('if_eq', [tmp_reg.x, stereo_const.x])
    tree.add_inst('texldl', [tmp_reg, stereo_const.z, tree.stereo_sampler])
    separation = tmp_reg.x; convergence = tmp_reg.y
    tree.add_inst('mov', [pos_adj, pos_reg])
    tree.add_inst('add', [tmp_reg.w, pos_adj.w, -convergence])
    tree.add_inst('mad', [pos_adj.x, tmp_reg.w, separation, pos_adj.x])
    for (t, r) in output_texcoords(tree):
        tree.add_inst('if_eq', [r, pos_reg])
        tree.add_inst('mov', [r, pos_adj])
        tree.add_inst('endif', [])
    if args.condition:
        tree.add_inst('endif', [])

def pos_to_line(tree, position):
    return len([ x for x in tree[:position] if isinstance(x, NewLine) ]) + 1

def prev_line_pos(tree, position):
    for p in range(position, -1, -1):
        if isinstance(tree[p], NewLine):
            return p + 1
    return 0

def next_line_pos(tree, position):
    for p in range(position, len(tree)):
        if isinstance(tree[p], NewLine):
            return p + 1
    return len(tree) + 1

def scan_shader(tree, reg, components=None, write=None, start=None, end=None, direction=1, stop=False):
    assert(direction == 1 or direction == -1)
    assert(write is not None)

    Match = collections.namedtuple('Match', ['line', 'token', 'instruction'])

    if direction == 1:
        if start is None:
            start = 0
        if end is None:
            end = len(tree)
        def direction_iter(input):
            return input
    else:
        if start is None:
            start = len(tree) - 1
        if end is None:
            end = -1
        def direction_iter(input):
            return reversed(list(input))

    tmp = reg
    if components:
        tmp += '.%s' % components
    debug_verbose(1, "Scanning shader %s from line %i to %i for %s %s..." % (
            {1: 'downwards', -1: 'upwards'}[direction],
            pos_to_line(tree, start), pos_to_line(tree, end - direction),
            {True: 'write to', False: 'read from'}[write],
            tmp,
    ))

    if isinstance(components, str):
        components = set(components)

    def is_match(other):
        return other.reg == reg and \
                (not components or not other.swizzle or \
                components.intersection(set(list(other.swizzle))))
        # FIXME: Also handle implied destination mask from
        # instructions that only write to one component

    ret = []
    for i in range(start, end, direction):
        line = tree[i]
        if not isinstance(line, SyntaxTree):
            continue
        for (j, instr) in direction_iter(enumerate(line)):
            if not isinstance(instr, Instruction):
                continue
            if instr.is_def_or_dcl():
                continue
            if not instr.args:
                continue
            # debug('scanning %s' % instr)
            if write:
                dest = instr.args[0]
                if is_match(dest):
                    debug_verbose(1, 'Found write to %s on line %s: %s' % (dest, pos_to_line(tree, i), instr))
                    ret.append(Match(i, j, instr))
                    if stop:
                        return ret
            else:
                for arg in instr.args[1:]:
                    if is_match(arg):
                        debug_verbose(1, 'Found read from %s on line %s: %s' % (arg, pos_to_line(tree, i), instr))
                        ret.append(Match(i, j, instr))
                        if stop:
                            return ret

    return ret

def auto_fix_vertex_halo(tree, args):
    # This attempts to automatically fix vertex shaders that are broken in a
    # very common way, where the output position has been copied to a texcoord.
    # This is not a magic bullet - it can only fix fairly simple cases of this
    # type of broken shader, but may be useful for fixing halos, Unity surface
    # shaders, etc.

    if not isinstance(tree, VS3):
        raise Exception('Auto texcoord adjustment is only applicable to vertex shaders')

    # 1. Find output position variable from declarations
    pos_out = find_declaration(tree, 'dcl_position', 'o')

    # 2. Locate where in the shader the output position is set and note which
    #    temporary register was copied to it.
    results = scan_shader(tree, pos_out, write=True)
    if not results:
        debug("Couldn't find write to output position register")
        return
    if len(results) > 1:
        # FUTURE: We may be able to handle certain cases of this
        debug_verbose(0, "Can't autofix a vertex shader writing to output position from multiple instructions")
        return
    (output_line, output_linepos, output_instr) = results[0]
    if output_instr.opcode != 'mov':
        debug_verbose(-1, 'Output not using mov instruction: %s' % output_instr)
        return
    temp_reg = output_instr.args[1]
    if not temp_reg.startswith('r'):
        debug_verbose(-1, 'Output not moved from a temporary register: %s' % output_instr)
        return

    # 3. Scan upwards to find where the X or W components of the temporary
    #    register was last set.
    results = scan_shader(tree, temp_reg.reg, components='xw', write=True, start=output_line - 1, direction=-1, stop=True)
    if not results:
        debug('WARNING: Output set from undefined register!!!?!')
        return
    (temp_reg_line, temp_reg_linepos, temp_reg_instr) = results[0]

    # 4. Scan between the two lines identified in 2 and 3 for any reads of the
    #    temporary register:
    results = scan_shader(tree, temp_reg.reg, write=False, start=temp_reg_line + 1, end=output_line)
    if results:
        # 5. If temporary register was read between temporary register being set
        #    and moved to output, relocate the output to just before the first
        #    line that read from the temporary register
        relocate_to = results[0][0]

        # 6. Scan for any writes to other components of the temporary register
        #    that we may have just moved the output register past, and copy
        #    these to the output position at the original output location.
        results = scan_shader(tree, temp_reg.reg, components='yzw', write=True, start=relocate_to + 1, end=output_line)
        if results:
            components = [ tuple(instr.args[0].swizzle) for (_, _, instr) in results ]
            components = ''.join(set(itertools.chain(*components)))
            tree.insert_instr(next_line_pos(tree, output_line))
            instr = NewInstruction('mov', ['%s.%s' % (pos_out.reg, components), '%s.%s' % (temp_reg.reg, components)])
            debug_verbose(-1, "Line %i: Inserting '%s'" % (pos_to_line(tree, output_line)+1, instr))
            tree.insert_instr(next_line_pos(tree, output_line), instr, 'Inserted by shadertool.py')

        # Actually do the relocation from 5 (FIXME: Move this up, being careful
        # of position offsets):
        line = tree[output_line]
        line.insert(0, CPPStyleComment('// '))
        line.append(WhiteSpace(' '))
        line.append(CPPStyleComment('// Relocated to line %i with shadertool.py' % pos_to_line(tree, relocate_to)))
        debug_verbose(-1, "Line %i: %s" % (pos_to_line(tree, output_line), tree[output_line]))
        tree.insert_instr(prev_line_pos(tree, output_line))
        debug_verbose(-1, "Line %i: Relocating '%s' to here" % (pos_to_line(tree, relocate_to), output_instr))
        relocate_to += tree.insert_instr(prev_line_pos(tree, relocate_to))
        tree.insert_instr(prev_line_pos(tree, relocate_to), output_instr, 'Relocated from line %i with shadertool.py' % pos_to_line(tree, output_line))
        output_line = relocate_to
    else:
        # 7. No reads above, scan downwards until temporary register X
        #    component is next set:
        results = scan_shader(tree, temp_reg.reg, components='x', write=True, start=output_line, stop=True)
        scan_until = len(tree)
        if results:
            scan_until = results[0].line

        # 8. Scan between the two lines identified by 2 and 7 for any reads of
        #    the temporary register:
        results = scan_shader(tree, temp_reg.reg, write=False, start=output_line + 1, end=scan_until, stop=True)
        if not results:
            debug_verbose(0, 'No other reads of temporary variable found, nothing to fix')
            return

    # 9. Insert stereo conversion after new location of move to output position.
    # FIXME: Refactor common code with the adjust_output, etc
    stereo_const, offset = insert_stereo_declarations(tree, args)
    pos = next_line_pos(tree, output_line + offset)
    t = tree._find_free_reg('r', VS3)

    debug_verbose(-1, 'Line %i: Applying stereo correction formula to %s' % (pos_to_line(tree, pos), temp_reg.reg))
    pos += insert_vanity_comment(args, tree, pos, "Automatic vertex shader halo fix inserted with")

    pos += tree.insert_instr(pos, NewInstruction('texldl', [t, stereo_const.z, tree.stereo_sampler]))
    separation = t.x; convergence = t.y
    pos += tree.insert_instr(pos, NewInstruction('add', [t.w, temp_reg.w, -convergence]))
    pos += tree.insert_instr(pos, NewInstruction('mad', [temp_reg.x, t.w, separation, temp_reg.x]))
    pos += tree.insert_instr(pos)

    tree.autofixed = True

def find_header(tree, comment_pattern):
    for line in range(tree.shader_start):
        for token in tree[line]:
            if not isinstance(token, CPPStyleComment):
                continue

            match = comment_pattern.match(token)
            if match is not None:
                return match
    raise KeyError()

unreal_NvStereoEnabled_pattern = re.compile(r'//\s+NvStereoEnabled\s+(?P<constant>c[0-9]+)\s+1$')
def disable_unreal_correction(tree, args, redundant_check):
    # In Life Is Strange I found a lot of Unreal Engine shaders are now using
    # the vPos semantic, and then applying a stereo correction on top of that,
    # which is wrong as vPos is already the correct screen location.

    if not isinstance(tree, PS3):
        raise Exception('Disabling redundant Unreal correction is only applicable to pixel shaders')

    if redundant_check:
        try:
            vPos = find_declaration(tree, 'dcl', 'vPos.xy')
        except IndexError:
            debug_verbose(0, 'Shader does not use vPos')
            return False

    try:
        match = find_header(tree, unreal_NvStereoEnabled_pattern)
    except KeyError:
        debug_verbose(0, 'Shader does not use NvStereoEnabled')
        return False

    constant = Register(match.group('constant'))
    debug_verbose(-1, 'Disabling NvStereoEnabled %s' % constant)

    if redundant_check:
        tree.decl_end += insert_vanity_comment(args, tree, tree.decl_end, "Redundant Unreal Engine stereo correction disabled by")
    else:
        tree.decl_end += insert_vanity_comment(args, tree, tree.decl_end, "Unreal Engine stereo correction disabled by")
    tree.insert_decl('def', [constant, 0, 0, 0, 0], comment='Overrides NvStereoEnabled passed from Unreal Engine')
    tree.insert_decl()

    tree.autofixed = True

    return True

unreal_TextureSpaceBlurOrigin_pattern = re.compile(r'//\s+TextureSpaceBlurOrigin\s+(?P<constant>c[0-9]+)\s+1$')
def auto_fix_unreal_light_shafts(tree, args):
    if not isinstance(tree, PS3):
        raise Exception('Unreal light shaft auto fix is only applicable to pixel shaders')

    try:
        match = find_header(tree, unreal_TextureSpaceBlurOrigin_pattern)
    except KeyError:
        debug_verbose(0, 'Shader does not use TextureSpaceBlurOrigin')
        return

    orig = Register(match.group('constant'))
    debug_verbose(0, 'TextureSpaceBlurOrigin identified as %s' % orig)

    results = scan_shader(tree, orig, write=False)
    if not results:
        debug_verbose(0, 'TextureSpaceBlurOrigin is not used in shader')
        return

    debug_verbose(-1, 'Applying Unreal Engine 3 light shaft fix')

    adj = tree._find_free_reg('r', PS3)
    t = tree._find_free_reg('r', PS3)
    stereo_const, _ = insert_stereo_declarations(tree, args, w = 0.5)

    replace_regs = {orig: adj}
    tree.do_replacements(replace_regs, False)

    pos = tree.decl_end
    pos += insert_vanity_comment(args, tree, tree.decl_end, "Unreal light shaft fix inserted with")
    pos += tree.insert_instr(pos, NewInstruction('texldl', [t, stereo_const.z, tree.stereo_sampler]))
    pos += tree.insert_instr(pos, NewInstruction('mov', [adj, orig]), comment='TextureSpaceBlurOrigin')
    pos += tree.insert_instr(pos, NewInstruction('mad', [adj.x, t.x, stereo_const.w, adj.x]), comment='Adjust each eye by 1/2 separation')
    pos += tree.insert_instr(pos)

    tree.autofixed = True

# Not sure if this is a generic UE3 thing, or specific to Life Is Strange
unreal_DNEReflectionTexture_pattern = re.compile(r'//\s+DNEReflectionTexture\s+(?P<sampler>s[0-9]+)\s+1$')
def auto_fix_unreal_dne_reflection(tree, args):
    if not isinstance(tree, PS3):
        raise Exception('Unreal DNE reflection fix is only applicable to pixel shaders')

    try:
        match = find_header(tree, unreal_DNEReflectionTexture_pattern)
    except KeyError:
        debug_verbose(0, 'Shader does not use DNEReflectionTexture')
        return

    orig = Register(match.group('sampler'))
    debug_verbose(0, 'DNEReflectionTexture identified as %s' % orig)

    results = scan_shader(tree, orig, write=False)
    if not results:
        debug_verbose(0, 'DNEReflectionTexture is not used in shader')
        return
    if len(results) > 1:
        debug("Autofixing a shader using DNEReflectionTexture multiple times is untested and disabled for safety. Please enable it, test and report back.")
        return

    debug_verbose(-1, 'Applying DNE reflection fix')

    t = tree._find_free_reg('r', PS3)
    stereo_const, offset = insert_stereo_declarations(tree, args, w = 0.5)

    for (sampler_line, sampler_linepos, sampler_instr) in results:
        orig_pos = pos = prev_line_pos(tree, sampler_line + offset)
        reg = sampler_instr.args[1]
        pos += insert_vanity_comment(args, tree, pos, "DNERefelctionTexture fix inserted with")
        pos += tree.insert_instr(pos, NewInstruction('texldl', [t, stereo_const.z, tree.stereo_sampler]))
        pos += tree.insert_instr(pos, NewInstruction('mad', [reg.x, -t.x, stereo_const.w, reg.x]))
        pos += tree.insert_instr(pos)
        offset += pos - orig_pos

        tree.autofixed = True

unreal_ScreenToShadowMatrix_pattern = re.compile(r'//\s+ScreenToShadowMatrix\s+(?P<constant>c[0-9]+)\s+4$')
def auto_fix_unreal_shadows(tree, args):
    if not isinstance(tree, PS3):
        raise Exception('Unreal shadow auto fix is only applicable to pixel shaders')

    try:
        match = find_header(tree, unreal_ScreenToShadowMatrix_pattern)
    except KeyError:
        debug_verbose(0, 'Shader does not use ScreenToShadowMatrix')
        return

    screen2shadow0 = Register(match.group('constant'))
    screen2shadow2 = Register('c%i' % (screen2shadow0.num + 2))
    debug_verbose(0, 'ScreenToShadowMatrix identified as %s %s' % (screen2shadow0, screen2shadow2))

    results0 = scan_shader(tree, screen2shadow0, write=False)
    results2 = scan_shader(tree, screen2shadow2, write=False)
    if not results0 or not results2:
        debug_verbose(0, 'ScreenToShadowMatrix is not used in shader')
        return
    if len(results0) > 1 or len(results2) > 1:
        debug("Autofixing a shader using ScreenToShadowMatrix multiple times is untested and disabled for safety. Please enable it, test and report back.")
        return

    (x_line, x_linepos, x_instr) = results0[0]
    (z_line, z_linepos, z_instr) = results2[0]

    if x_instr.opcode != 'mad' or z_instr.opcode != 'mad':
        debug('ScreenToShadowMatrix used in an unexpected way (column-major/row-major?)')
        return

    if x_instr.args[1] == screen2shadow0:
        x_reg = x_instr.args[2]
    elif x_instr.args[2] == screen2shadow0:
        x_reg = x_instr.args[1]
    else:
        debug('ScreenToShadowMatrix[0] used in an unexpected way')
        return

    if z_instr.args[1] == screen2shadow2:
        w_reg = z_instr.args[2]
    elif z_instr.args[2] == screen2shadow2:
        w_reg = z_instr.args[1]
    else:
        debug('ScreenToShadowMatrix[2] used in an unexpected way')
        return

    debug_verbose(-1, 'Applying Unreal Engine 3 shadow fix')

    try:
        vPos = find_declaration(tree, 'dcl', 'vPos.xy')
    except IndexError:
        vPos = None

    t = tree._find_free_reg('r', PS3)
    stereo_const, offset = insert_stereo_declarations(tree, args, w = 0.5)
    if vPos is None:
        texcoord = find_declaration(tree, 'dcl_texcoord', 'v')

        mask = ''
        if texcoord.swizzle:
            mask = '.%s' % texcoord.swizzle
        texcoord_adj = tree._find_free_reg('r', PS3)

        replace_regs = {texcoord.reg: texcoord_adj}
        tree.do_replacements(replace_regs, False)

    orig_offset = tree.decl_end
    vanity_inserted = disable_unreal_correction(tree, args, False)

    pos = tree.decl_end
    if vPos is None:
        if not vanity_inserted:
            pos += insert_vanity_comment(args, tree, tree.decl_end, "Unreal Engine shadow fix inserted with")
        pos += tree.insert_instr(pos, NewInstruction('texldl', [t, stereo_const.z, tree.stereo_sampler]))
        pos += tree.insert_instr(pos, NewInstruction('mov', [texcoord_adj + mask, texcoord.reg]))
        pos += tree.insert_instr(pos, NewInstruction('add', [t.w, texcoord_adj.w, -t.y]))
        pos += tree.insert_instr(pos, NewInstruction('mad', [texcoord_adj.x, t.w, t.x, texcoord_adj.x]))
        pos += tree.insert_instr(pos)
    offset += pos - orig_offset

    line = min(x_line, z_line)
    orig_pos = pos = prev_line_pos(tree, line + offset)
    pos += insert_vanity_comment(args, tree, pos, "Unreal Engine shadow fix inserted with")
    pos += tree.insert_instr(pos, NewInstruction('add', [t.w, w_reg, -t.y]))
    pos += tree.insert_instr(pos, NewInstruction('mad', [x_reg, -t.w, t.x, x_reg]))
    pos += tree.insert_instr(pos)
    offset += pos - orig_pos

    tree.autofixed = True

def add_unity_autofog_VS3(tree, reason):
    try:
        d = find_declaration(tree, 'dcl_fog')
        debug_verbose(0, 'Shader already has a fog output: %s' % d)
        return
    except:
        pass

    if 'o' in tree.reg_types and 'o9' in tree.reg_types['o']:
        debug('Shader already uses output o9')
        return

    pos_out = find_declaration(tree, 'dcl_position', 'o')

    results = scan_shader(tree, pos_out, write=True)
    if len(results) != 1:
        debug_verbose(0, 'Output position written from %i instructions (only exactly 1 write currently supported)' % len(results))
        return
    (output_line, output_linepos, output_instr) = results[0]
    if output_instr.opcode != 'mov':
        debug('Output not using mov instruction: %s' % output_instr)
        return
    temp_reg = output_instr.args[1]
    if not temp_reg.startswith('r'):
        debug('Output not moved from a temporary register: %s' % output_instr)
        return

    tree.fog_type = 'FOG'
    fog_output = NewInstruction('mov', [Register('o9'), temp_reg.z])
    tree.insert_instr(next_line_pos(tree, output_line), fog_output, 'Inserted by shadertool.py %s' % reason)
    debug_verbose(-1, "Line %i: %s" % (pos_to_line(tree, output_line+2), tree[output_line+2]))
    decl = NewInstruction('dcl_fog', [Register('o9')])
    # Inserting this in a specific spot to match Unity rather than using
    # insert_decl(), so manually increment decl_end as well:
    tree.decl_end += tree.insert_instr(next_line_pos(tree, tree.shader_start), decl, 'Inserted by shadertool.py %s' % reason)

def add_unity_autofog_PS3(tree, mad_fog, reason):
    try:
        d = find_declaration(tree, 'dcl_fog')
        debug_verbose(0, 'Shader already has a fog input: %s' % d)
        return
    except:
        pass

    if 'v' in tree.reg_types and 'v9' in tree.reg_types['v']:
        debug('Shader already uses input v9')
        return

    if 'r' in tree.reg_types and 'r30' in tree.reg_types['r']:
        debug('Shader already uses temporary register r30')
        return

    if 'r' in tree.reg_types and 'r31' in tree.reg_types['r']:
        debug('Shader already uses temporary register r31')
        return

    fog_c1 = tree._find_free_reg('c', None)
    fog_c2 = tree._find_free_reg('c', None)

    if fog_c2.num != fog_c1.num + 1:
        debug('Discontiguous free constants, not sure how Unity handles this edge case so aborting')
        return

    decl = NewInstruction('dcl_fog', ['v9.x'])
    tree.insert_instr(next_line_pos(tree, tree.shader_start), decl, 'Inserted by shadertool.py %s' % reason)

    replace_regs = {'oC0': Register('r30')}
    tree.do_replacements(replace_regs, False)

    pos = len(tree) + 1

    def add_instr(opcode, args):
        return tree.insert_instr(pos, NewInstruction(opcode, args))

    pos += tree.insert_instr(pos, None, 'Inserted by shadertool.py %s:' % reason)

    if mad_fog:
        tree.fog_type = 'MAD_FOG'
        pos += add_instr('mad_sat', ['r31.x', fog_c2.z, 'v9.x', fog_c2.w])
    else:
        tree.fog_type = 'EXP_FOG'
        pos += add_instr('mul', ['r31.x', fog_c2.x, 'v9.x'])
        pos += add_instr('mul', ['r31.x', 'r31.x', 'r31.x'])
        pos += add_instr('exp_sat', ['r31.x', '-r31.x'])

    debug_verbose(-1, "Inserting pixel shader fog instructions (%s)" % tree.fog_type)

    pos += add_instr('lrp', ['r30.xyz', 'r31.x', 'r30', fog_c1])
    pos += add_instr('mov', ['oC0', 'r30'])

def add_unity_autofog(tree, reason = 'to match Unity autofog'):
    '''
    Adds instructions to a shader to match those Unity automatically adds for
    fog. Used by extract_unity_shaders.py to construct fog variants of shaders.
    Returns a tuple of trees with each type of fog added.
    '''
    if not hasattr(tree, 'reg_types'):
        tree.analyse_regs()
    if isinstance(tree, VS3):
        add_unity_autofog_VS3(tree, reason)
        return (tree,)
    if isinstance(tree, PS3):
        tree1 = copy.deepcopy(tree)
        tree2 = copy.deepcopy(tree)
        add_unity_autofog_PS3(tree1, True, reason)
        add_unity_autofog_PS3(tree2, False, reason)
        return (tree1, tree2)
    return (tree,)

def _disable_output(tree, reg, args, stereo_const, tmp_reg):
    pos_reg = tree._find_free_reg('r', VS3)

    if reg.startswith('dcl_texcoord'):
        reg = find_declaration(tree, reg, 'o').reg
    if reg.startswith('texcoord'):
        reg = find_declaration(tree, 'dcl_%s' % reg, 'o').reg

    disabled = stereo_const.xxxx

    append_vanity_comment(args, tree, 'Texcoord disabled by')
    tree.add_inst('texldl', [tmp_reg, stereo_const.z, tree.stereo_sampler])
    separation = tmp_reg.x
    tree.add_inst('if_ne', [separation, -separation]) # Only disable in 3D
    if args.condition:
        tree.add_inst('mov', [tmp_reg.w, args.condition])
        tree.add_inst('if_eq', [tmp_reg.w, stereo_const.x])
    tree.add_inst('mov', [reg, disabled])
    if args.condition:
        tree.add_inst('endif', [])
    tree.add_inst('endif', [])

def disable_output(tree, args):
    if not isinstance(tree, VS3):
        raise Exception('Texcoord adjustment must be done on a vertex shader (currently)')

    stereo_const, _ = insert_stereo_declarations(tree, args)

    tmp_reg = tree._find_free_reg('r', VS3)

    for reg in args.disable_output:
        _disable_output(tree, reg, args, stereo_const, tmp_reg)

def disable_shader(tree, args):
    if isinstance(tree, VS3):
        reg = find_declaration(tree, 'dcl_position', 'o')
        if not reg.swizzle:
            reg = '%s.xyzw' % reg.reg
    elif isinstance(tree, PS3):
        reg = 'oC0.xyzw'
    else:
        raise Exception("Shader must be a vs_3_0 or a ps_3_0, but it's a %s" % shader.__class__.__name__)

    # FUTURE: Maybe search for an existing 0 or 1...
    stereo_const, _ = insert_stereo_declarations(tree, args)
    tmp_reg = tree._find_free_reg('r', VS3)

    append_vanity_comment(args, tree, 'Shader disabled by')
    if args.disable == '0':
        disabled = stereo_const.xxxx
    if args.disable == '1':
        disabled = stereo_const.yyyy

    tree.add_inst('texldl', [tmp_reg, stereo_const.z, tree.stereo_sampler])
    separation = tmp_reg.x
    tree.add_inst('if_ne', [separation, -separation]) # Only disable in 3D
    if args.condition:
        tree.add_inst('mov', [tmp_reg.w, args.condition])
        tree.add_inst('if_eq', [tmp_reg.w, stereo_const.x])
    tree.add_inst('mov', [reg, disabled])
    if args.condition:
        tree.add_inst('endif', [])
    tree.add_inst('endif', [])

def lookup_header_json(tree, index, file):
    if len(tree) and len(tree[0]) and isinstance(tree[0][0], CPPStyleComment) \
            and tree[0][0].startswith('// CRC32'):
                debug_verbose(0, '%s appears to already contain headers' % file)
                return tree

    crc = shaderutil.get_filename_crc(file)
    try:
        headers = index[crc]
    except:
        debug('%s not found in header index' % crc)
        return tree
    headers = [ (CPPStyleComment(x), NewLine('\n')) for x in headers.split('\n') ]
    headers = type(tree)(itertools.chain(*headers), None)
    headers.append(NewLine('\n'))
    headers.shader_start = len(headers) + tree.shader_start
    headers.decl_end = len(headers) + tree.decl_end
    headers.extend(tree)
    return headers

def update_ini(tree):
    '''
    Right now this just updates our internal data structures to note any
    changes we need to make to the ini file and we print these out before
    exiting. TODO: Actually update the ini file for real (still should notify
    the user).
    '''
    if not hasattr(tree, 'ini'):
        return

    if isinstance(tree, VertexShader):
        acronym = 'VS'
    elif isinstance(tree, PixelShader):
        acronym = 'PS'
    else:
        raise AssertionError()

    crc = shaderutil.get_filename_crc(tree.filename)
    section = '%s%s' % (acronym, crc)
    dx9settings_ini.setdefault(section, [])
    for (k, v, comment) in tree.ini:
        dx9settings_ini[section].append('; %s' % comment)
        dx9settings_ini[section].append((k, v))

def do_ini_updates():
    if not dx9settings_ini:
        return

    # TODO: Merge these into the ini file directly. Still print a message
    # for the user so they know what we've done.
    debug()
    debug()
    debug('!' * 79)
    debug('!' * 12 + ' Please add the following lines to the DX9Settings.ini ' + '!' * 12)
    debug('!' * 79)
    debug()
    for section in dx9settings_ini:
        debug('[%s]' % section)
        for line in dx9settings_ini[section]:
            if isinstance(line, tuple):
                debug('%s = %s' % line)
            else:
                debug(line)
        debug()

def parse_args():
    global verbosity

    parser = argparse.ArgumentParser(description = 'nVidia 3D Vision Shaderhacker Tool')
    parser.add_argument('files', nargs='+',
            help='List of shader assembly files to process')
    parser.add_argument('--install', '-i', action='store_true',
            help='Install shaders in ShaderOverride directory')
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

    parser.add_argument('--stereo-sampler-vs',
            help='Specify the sampler to read the stereo parameters from in vertex shaders')
    parser.add_argument('--stereo-sampler-ps',
            help='Specify the sampler to read the stereo parameters from in pixel shaders')

    parser.add_argument('--show-regs', '-r', action='store_true',
            help='Show the registers used in the shader')
    parser.add_argument('--find-free-consts', '--consts', '-c', action='store_true',
            help='Search for unused constants')
    parser.add_argument('--disable', choices=['0', '1'], nargs='?', default=None, const='0',
            help="Disable a shader, by setting it's output to 0 or 1")
    parser.add_argument('--disable-output', '--disable-texcoord', action='append',
            help="Disable a given texcoord in the shader")
    parser.add_argument('--adjust', '--adjust-output', '--adjust-texcoord', action='append',
            help="Apply the stereo formula to an output (texcoord or position)")
    parser.add_argument('--adjust-multiply', '--adjust-multiplier', '--multiply', type=float,
            help="Multiplier for the stereo adjustment. If you notice the broken effect switches eyes try 0.5")
    parser.add_argument('--unadjust', action='append', nargs='?', default=None, const='position',
            help="Unadjust the output. Equivalent to --adjust=<output> --adjust-multiply=-1")
    parser.add_argument('--condition',
            help="Make adjustments conditional on the given register passed in from DX9Settings.ini")
    parser.add_argument('--no-mad', action='store_false', dest='use_mad',
            help="Use mad instruction to make stereo correction more concise")
    parser.add_argument('--auto-adjust-texcoords', action='store_true',
            help="Adjust any texcoord that matches the output position from a vertex shader")
    parser.add_argument('--auto-fix-vertex-halo', action='store_true',
            help="Attempt to automatically fix a vertex shader for common halo type issues")
    parser.add_argument('--disable-redundant-unreal-correction', action='store_true',
            help="Disable the stereo correction in Unreal Engine pixel shaders that also use the vPos semantic")
    parser.add_argument('--auto-fix-unreal-light-shafts', action='store_true',
            help="Attempt to automatically fix light shafts found in Unreal games")
    parser.add_argument('--auto-fix-unreal-dne-reflection', action='store_true',
            help="Attempt to automatically fix reflective floor surfaces found in Unreal games")
    parser.add_argument('--auto-fix-unreal-shadows', action='store_true',
            help="Attempt to automatically fix shadows in Unreal games")
    parser.add_argument('--only-autofixed', action='store_true',
            help="Installation type operations only act on shaders that were successfully autofixed with --auto-fix-vertex-halo")

    parser.add_argument('--add-unity-autofog', action='store_true',
            help="Add instructions to the shader to support fog, like Unity does (used by extract_unity_shaders.py)")
    parser.add_argument('--add-fog-on-sm3-update', action='store_true',
            help="Add fog instructions to any vertex shader being upgraded from vs_2_0 to vs_3_0 - use if fog disappears on a shader after running through this tool")

    parser.add_argument('--no-convert', '--noconv', action='store_false', dest='auto_convert',
            help="Do not automatically convert shaders to shader model 3")
    parser.add_argument('--lookup-header-json', type=argparse.FileType('r'), # XXX: When python 3.4 comes to cygwin, add encoding='utf-8'
            help="Look up headers in a JSON index, such as those created with extract_unity_shaders.py and prepend them.\n" +
            "Implies --no-convert --in-place if no other installation options were provided")
    parser.add_argument('--original', action='store_true',
            help="Look for the original shader from Dumps/AllDumps and work as though it had been specified instead")
    parser.add_argument('--restore-original', '--restore-original-shader', action='store_true',
            help="Look for an original copy of the shader in the Dumps/AllShaders directory and copies it over the top of this one\n" +
            "Game must have been run with DumpAll=true in the past. Implies --in-place --no-convert")
    parser.add_argument('--adjust-ui-depth', '--ui',
            help='Adjust the output depth of this shader to a percentage of separation passed in from DX9Settings.ini')

    parser.add_argument('--debug-tokeniser', action='store_true',
            help='Dumps the shader broken up into tokens')
    parser.add_argument('--debug-syntax-tree', action='store_true',
            help='Dumps the syntax tree')
    parser.add_argument('--ignore-parse-errors', action='store_true',
            help='Continue with the next file in the event of a parse error')
    parser.add_argument('--ignore-register-errors', action='store_true',
            help='Continue with the next file in the event that a fix cannot be applied due to running out of registers')

    parser.add_argument('--verbose', '-v', action='count', default=0,
            help='Level of verbosity')
    parser.add_argument('--quiet', '-q', action='count', default=0,
            help='Suppress usual informational messages. Specify multiple times to suppress more messages.')
    args = parser.parse_args()

    if not args.output and not args.in_place and not args.install and not \
            args.install_to and not args.to_git and not args.find_free_consts \
            and not args.show_regs and not args.debug_tokeniser and not \
            args.debug_syntax_tree and not args.restore_original:
        parser.error("did not specify anything to do (e.g. --install, --install-to, --in-place, --output, --show-regs, etc)");

    if args.to_git:
        if not args.output and not args.install and not args.install_to and not args.to_git:
            args.auto_convert = False

    if args.lookup_header_json:
        args.lookup_header_json = json.load(args.lookup_header_json)
        if not args.output and not args.install and not args.install_to and not args.to_git:
            args.in_place = True
            args.auto_convert = False

    args.precheck_installed = False
    if args.install and not args.force and not args.output and not args.install_to and not args.to_git:
        args.precheck_installed = True

    if args.restore_original:
        args.auto_convert = False

    if args.add_unity_autofog:
        args.auto_convert = False

    verbosity = args.verbose - args.quiet

    return args

def args_require_reg_analysis(args):
        return args.show_regs or \
                args.find_free_consts or \
                args.adjust_ui_depth or \
                args.disable or \
                args.disable_output or \
                args.adjust or \
                args.unadjust or \
                args.auto_adjust_texcoords or \
                args.auto_fix_vertex_halo or \
                args.add_unity_autofog or \
                args.disable_redundant_unreal_correction or \
                args.auto_fix_unreal_light_shafts or \
                args.auto_fix_unreal_dne_reflection or \
                args.auto_fix_unreal_shadows

        # Also needs register analysis, but earlier than this test:
        # args.add_fog_on_sm3_update

processed = set()

def main():
    args = parse_args()

    if args.find_free_consts:
        free_ps_consts = RegSet([ Register('c%d' % c) for c in range(PS3.max_regs['c']) ])
        free_vs_consts = RegSet([ Register('c%d' % c) for c in range(VS3.max_regs['c']) ])
        local_ps_consts = free_ps_consts.copy()
        local_vs_consts = free_vs_consts.copy()
        address_reg_vs = RegSet()
        address_reg_ps = RegSet()
        checked_ps = checked_vs = False

    # Windows command prompt passes us a literal *, so expand any that we were passed:
    f = []
    for file in args.files:
        if '*' in file:
            f.extend(glob.glob(file))
        else:
            f.append(file)
    args.files = f

    for file in args.files:
        try:
            crc = shaderutil.get_filename_crc(file)
        except shaderutil.NoCRCError:
            pass
        else:
            if crc in processed:
                debug_verbose(1, 'Skipping %s - CRC already processed' % file)
                continue
            processed.add(crc)

        if args.precheck_installed and check_shader_installed(file):
            debug_verbose(0, 'Skipping %s - already installed and you did not specify --force' % file)
            continue

        if args.restore_original:
            debug('Restoring %s...' % file)
            restore_original_shader(file)
            continue

        real_file = file
        if args.original:
            file = find_original_shader(file)

        debug_verbose(-2, 'parsing %s...' % file)
        try:
            if file == '-':
                tree = parse_shader(sys.stdin.read(), args)
            else:
                tree = parse_shader(open(file, 'r', newline=None).read(), args)
        except Exception as e:
            if args.ignore_parse_errors:
                import traceback, time
                traceback.print_exc()
                time.sleep(0.1)
                continue
            do_ini_updates()
            raise
        if args.auto_convert and hasattr(tree, 'to_shader_model_3'):
            debug_verbose(0, 'Converting to Shader Model 3...')
            tree.to_shader_model_3(args)
        if args.debug_syntax_tree:
            debug(repr(tree), end='')

        if args.lookup_header_json:
            tree = lookup_header_json(tree, args.lookup_header_json, file)

        if args_require_reg_analysis(args):
            tree.analyse_regs(args.show_regs)
            if args.find_free_consts:
                if isinstance(tree, VS3):
                    checked_vs = True
                    local_vs_consts = local_vs_consts.difference(tree.global_consts)
                    free_vs_consts = free_vs_consts.difference(tree.consts)
                    address_reg_vs.update(tree.addressed_regs)
                elif isinstance(tree, PS3):
                    checked_ps = True
                    local_ps_consts = local_ps_consts.difference(tree.global_consts)
                    free_ps_consts = free_ps_consts.difference(tree.consts)
                    address_reg_ps.update(tree.addressed_regs)
                else:
                    raise Exception("Shader must be a vs_3_0 or a ps_3_0, but it's a %s" % shader.__class__.__name__)

        tree.filename = file

        try:
            if args.add_unity_autofog:
                # FIXME: Output both types on pixel shader fog or make selectable
                tree = add_unity_autofog(tree)[0]
            if args.disable:
                disable_shader(tree, args)
            if args.auto_adjust_texcoords:
                auto_adjust_texcoords(tree, args)
            tree.autofixed = False
            if args.auto_fix_vertex_halo:
                auto_fix_vertex_halo(tree, args)
            if args.disable_redundant_unreal_correction:
                disable_unreal_correction(tree, args, True)
            if args.auto_fix_unreal_light_shafts:
                auto_fix_unreal_light_shafts(tree, args)
            if args.auto_fix_unreal_dne_reflection:
                auto_fix_unreal_dne_reflection(tree, args)
            if args.auto_fix_unreal_shadows:
                auto_fix_unreal_shadows(tree, args)
            if args.adjust_ui_depth:
                adjust_ui_depth(tree, args)
            if args.disable_output:
                disable_output(tree, args)
            if args.adjust:
                adjust_output(tree, args)
            if args.unadjust:
                a = copy.copy(args)
                a.adjust = args.unadjust
                a.adjust_multiply = -1
                adjust_output(tree, a)
        except NoFreeRegisters as e:
            if args.ignore_register_errors:
                import traceback, time
                traceback.print_exc()
                time.sleep(0.1)
                continue
            raise

        if not args.only_autofixed or tree.autofixed:
            if args.output:
                print(tree, end='', file=args.output)
                update_ini(tree)
            if args.in_place:
                tmp = '%s.new' % real_file
                print(tree, end='', file=open(tmp, 'w'))
                os.rename(tmp, real_file)
                update_ini(tree)
            if args.install:
                if install_shader(tree, file, args):
                    update_ini(tree)
            if args.install_to:
                if install_shader_to(tree, file, args, os.path.expanduser(args.install_to), True):
                    update_ini(tree)
            if args.to_git:
                a = copy.copy(args)
                a.force = True
                if install_shader_to_git(tree, file, a):
                    update_ini(tree)

    if args.find_free_consts:
        if checked_vs:
            local_vs_consts = local_vs_consts.difference(free_vs_consts)
            debug('\nFree Vertex Shader Constants:')
            debug(', '.join(sorted(free_vs_consts)))
            debug('\nLocal only Vertex Shader Constants:')
            debug(', '.join(sorted(local_vs_consts)))
            if address_reg_vs:
                debug('\nCAUTION: Address reg was applied offset from these consts:')
                debug(', '.join(sorted(address_reg_vs)))
        if checked_ps:
            local_ps_consts = local_ps_consts.difference(free_ps_consts)
            debug('\nFree Pixel Shader Constants:')
            debug(', '.join(sorted(free_ps_consts)))
            debug('\nLocal only Pixel Shader Constants:')
            debug(', '.join(sorted(local_ps_consts)))
            if address_reg_ps:
                debug('\nCAUTION: Address reg was applied offset from these consts:')
                debug(', '.join(sorted(address_reg_ps)))

    do_ini_updates()

if __name__ == '__main__':
    sys.exit(main())

# vi: et ts=4:sw=4
