#!/usr/bin/env python3

import sys, os, re, argparse

import shaderutil

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

def debug(*args, **kwargs):
    print(file=sys.stderr, *args, **kwargs)

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
    pattern = re.compile(r'[a-zA-Z_\-][a-zA-Z_0-9\.\[\]]*')

class Comma(Token):
    pattern = re.compile(r',')

class Float(Token, Number):
    pattern = re.compile(r'-?[0-9]*\.[0-9]*(e[-+]?[0-9]+)?')

class Int(Token, Number):
    pattern = re.compile(r'-?[0-9]+')

class CPPStyleComment(Token, Ignore):
    pattern = re.compile(r'\/\/.*$', re.MULTILINE)

class CStyleComment(Token, Ignore): # XXX: Are these valid in shader asm language?
    pattern = re.compile(r'\/\*.*\*\/', re.MULTILINE)

class WhiteSpace(Token, Ignore):
    pattern = re.compile(r'\s+')

class NewLine(WhiteSpace, InstructionSeparator):
    pattern = re.compile(r'\n')

class SemiColon(Token, InstructionSeparator): # XXX: Is this a valid separator in shader asm?
    pattern = re.compile(r';')

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
    CStyleComment, # XXX: Are these valid in shader asm?
    NewLine,
    WhiteSpace,
    Comma,
    SemiColon, # XXX: Is this a valid separator in shader asm?
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
        (?P<type>[a-zA-Z]+)
        (?P<num>\d*)
        (?P<absolute>_abs)?
        (?P<address_reg>
            \[a0
                (?:\.[abcdxyzw]{1,4})?
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
        ret.absolute = match.group('absolute') or ''
        ret.type = match.group('type')
        ret.num = match.group('num')
        ret.reg = ret.type + ret.num
        ret.address_reg = match.group('address_reg')
        if ret.num:
            ret.num = int(ret.num)
        ret.swizzle = match.group('swizzle')
        return ret

    def __lt__(self, other):
        if isinstance(self.num, int) and isinstance(other.num, int):
            return self.num < other.num
        return str.__lt__(self, other)

    @staticmethod
    def _str(negate, reg, absolute, swizzle):
        r = '%s%s%s' % (negate, reg, absolute) # FIXME: Sync type and num if reg changed
        if swizzle:
            r += '.%s' % swizzle
        return r

    def __str__(self):
        return self._str(self.negate, self.reg, self.absolute, self.swizzle)

    def __neg__(self):
        if self.negate:
            negate = ''
        else:
            negate = '-'
        return Register(self._str(negate, self.reg, self.absolute, self.swizzle))

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
    def __init__(self, tree):
        newtree = []
        self.decl_end = 0
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

    def insert_decl(self, *inst):
        if inst:
            self.insert(self.decl_end, SyntaxTree([NewInstruction(*inst)]))
            self.decl_end += 1
        self.insert(self.decl_end, NewLine('\n'))
        self.decl_end += 1

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

    def _find_free_reg(self, type, model):
        if type not in self.reg_types:
            r = Register(type + '0')
            self.reg_types[type] = RegSet([r])
            return r

        taken = self.reg_types[type]
        for num in range(model.max_regs[type]):
            reg = type + str(num)
            if reg not in taken:
                r = Register(reg)
                taken.add(r)
                return r

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

class VS3(ShaderBlock):
    max_regs = { # http://msdn.microsoft.com/en-us/library/windows/desktop/bb172963(v=vs.85).aspx
        'c': 256,
        'i': 16,
        'o': 12,
        'r': 32,
        's': 4,
        'v': 16,
    }
    def_stereo_sampler = 's0'

class PS3(ShaderBlock):
    max_regs = { # http://msdn.microsoft.com/en-us/library/windows/desktop/bb172920(v=vs.85).aspx
        'c': 224,
        'i': 16,
        'r': 32,
        's': 16,
        'v': 12,
    }
    def_stereo_sampler = 's13'

class VS2(ShaderBlock):
    def to_shader_model_3(self):
        self.analyse_regs()
        self.insert_decl()
        replace_regs = {}

        if 'oT' in self.reg_types:
            for reg in sorted(self.reg_types['oT']):
                opcode = 'dcl_texcoord'
                if reg.num:
                    opcode = 'dcl_texcoord%d' % reg.num
                out = self._find_free_reg('o', VS3)
                self.insert_decl(opcode, [out])
                replace_regs[reg.reg] = out

        if 'oPos' in self.reg_types:
            out = self._find_free_reg('o', VS3)
            self.insert_decl('dcl_position', [out])
            replace_regs['oPos'] = out


        if 'oD' in self.reg_types:
            for reg in sorted(self.reg_types['oD']):
                opcode = 'dcl_color'
                if reg.num:
                    opcode = 'dcl_color%d' % reg.num
                out = self._find_free_reg('o', VS3)
                self.insert_decl(opcode, [out])
                replace_regs[reg.reg] = out

        if 'oFog' in self.reg_types:
            out = self._find_free_reg('o', VS3)
            self.insert_decl('dcl_fog', [out])
            replace_regs['oFog'] = out
        if 'oPts' in self.reg_types:
            out = self._find_free_reg('o', VS3)
            self.insert_decl('dcl_psize', [out])
            replace_regs['oPts'] = out

        self.insert_decl()

        self.do_replacements(replace_regs, True, {'vs_2_0': 'vs_3_0'},
                {'sincos': fixup_sincos})
        self.__class__ = VS3

class PS2(ShaderBlock):
    def to_shader_model_3(self):
        def fixup_ps2_dcl(tree, node, parent, idx):
            node.opcode = 'dcl_texcoord'
            reg = node.args[0]
            if reg.type != 't':
                return
            if reg.num:
                node.opcode = 'dcl_texcoord%d' % reg.num
            node[0] = node.opcode
        self.analyse_regs()
        replace_regs = {}

        for reg in sorted(self.reg_types['t']):
            replace_regs[reg.reg] = Register('v%d' % reg.num)

        self.do_replacements(replace_regs, True, {'ps_2_0': 'ps_3_0'},
                {'sincos': fixup_sincos, 'dcl': fixup_ps2_dcl})
        self.__class__ = PS3

sections = {
    'vs_3_0': VS3,
    'ps_3_0': PS3,
    'vs_2_0': VS2,
    'ps_2_0': PS2,
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
                return sections[token](head + preshader + tree[lineno:])
            elif preshader_start is None:
                raise SyntaxError('Unexpected token while searching for shader type: %s' % token)
    raise SyntaxError('Unable to identify shader type')

def parse_shader(shader, args):
    tokens = tokenise(shader)
    if args.debug_tokeniser:
        for token in tokens:
            debug('%s: %s' % (token.__class__.__name__, repr(str(token))))
    tree = SyntaxTree(tokens)
    tree = SyntaxTree.split_newlines(tree)
    tree = process_sections(tree)
    return tree

def install_shader(shader, file, args):
    dest_name = '%s.txt' % shaderutil.get_filename_crc(file)

    src_dir = os.path.dirname(os.path.join(os.curdir, file))
    dumps = os.path.realpath(os.path.join(src_dir, '../..'))
    if os.path.basename(dumps).lower() != 'dumps':
        raise Exception("Not installing %s - not in a Dumps directory" % file)
    gamedir = os.path.realpath(os.path.join(src_dir, '../../..'))

    override_dir = os.path.join(gamedir, 'ShaderOverride')
    try:
        os.mkdir(override_dir)
    except OSError:
        pass

    if isinstance(shader, VS3):
        shader_dir = os.path.join(override_dir, 'VertexShaders')
    elif isinstance(shader, PS3):
        shader_dir = os.path.join(override_dir, 'PixelShaders')
    else:
        raise Exception("Shader must be a vs_3_0 or a ps_3_0, but it's a %s" % shader.__class__.__name__)
    try:
        os.mkdir(shader_dir)
    except OSError:
        pass

    dest = os.path.join(shader_dir, dest_name)
    if not args.force and os.path.exists(dest):
        debug('Skipping %s - already installed' % file)
        return

    debug('Installing to %s...' % os.path.relpath(dest, os.path.join(gamedir, '..')))
    print(shader, end='', file=open(dest, 'w'))

def insert_stereo_declarations(tree, args, x=0, y=1, z=0.0625, w=0.5):
    if hasattr(tree, 'stereo_const'):
        return tree.stereo_const
    if args.adjust_multiply:
        w = args.adjust_multiply
    tree.stereo_const = tree._find_free_reg('c', VS3)
    tree.insert_decl()
    tree.insert_decl('def', [tree.stereo_const, x, y, z, w])
    tree.insert_decl('dcl_2d', [tree.def_stereo_sampler])
    tree.insert_decl()
    return tree.stereo_const

def append_inserted_by_comment(tree, what):
    tree.add_inst()
    tree.append(CPPStyleComment("// %s DarkStarSword's shadertool.py:" % what))
    tree.append(NewLine('\n'))
    tree.append(CPPStyleComment('// %s %s' % (os.path.basename(sys.argv[0]), ' '.join(sys.argv[1:]))))
    tree.append(NewLine('\n'))

def find_declaration(tree, type, prefix):
    for (t, r) in tree.declared:
        if t == type:
            if prefix and not r.startswith(prefix):
                continue
            return r
    raise IndexError()

def adjust_ui_depth(tree, args):
    if not isinstance(tree, VS3):
        raise Exception('UI Depth adjustment must be done on a vertex shader')

    stereo_const = insert_stereo_declarations(tree, args)

    pos_reg = tree._find_free_reg('r', VS3)
    tmp_reg = tree._find_free_reg('r', VS3)
    dst_reg = find_declaration(tree, 'dcl_position', 'o').reg

    replace_regs = {dst_reg: pos_reg}
    tree.do_replacements(replace_regs, False)

    append_inserted_by_comment(tree, 'UI depth adjustment inserted with')
    tree.add_inst('texldl', [tmp_reg, stereo_const.z, tree.def_stereo_sampler])
    separation = tmp_reg.x
    tree.add_inst('mad', [pos_reg.x, separation, args.adjust_ui_depth, pos_reg.x])
    tree.add_inst('mov', [dst_reg, pos_reg])

def _adjust_texcoord(tree, reg, args, stereo_const, tmp_reg):
    pos_reg = tree._find_free_reg('r', VS3)

    if reg.startswith('dcl_texcoord'):
        dst_reg = find_declaration(tree, reg, 'o').reg
    if reg.startswith('texcoord'):
        dst_reg = find_declaration(tree, 'dcl_%s' % reg, 'o').reg
    else:
        dst_reg = reg
    replace_regs = {dst_reg: pos_reg}
    tree.do_replacements(replace_regs, False)

    append_inserted_by_comment(tree, 'Texcoord adjustment inserted with')
    if args.condition:
        tree.add_inst('mov', [tmp_reg.x, args.condition])
        tree.add_inst('if_eq', [tmp_reg.x, stereo_const.x])
    tree.add_inst('texldl', [tmp_reg, stereo_const.z, tree.def_stereo_sampler])
    separation = tmp_reg.x; convergence = tmp_reg.y
    tree.add_inst('add', [tmp_reg.w, pos_reg.w, -convergence])
    if args.use_mad and not args.adjust_multiply:
        tree.add_inst('mad', [pos_reg.x, tmp_reg.w, separation, pos_reg.x])
    else:
        tree.add_inst('mul', [tmp_reg.w, tmp_reg.w, separation])
        if args.adjust_multiply:
            tree.add_inst('mul', [tmp_reg.w, tmp_reg.w, stereo_const.w])
        tree.add_inst('add', [pos_reg.x, pos_reg.x, tmp_reg.w])
    if args.condition:
        tree.add_inst('endif', [])
    tree.add_inst('mov', [dst_reg, pos_reg])

def adjust_texcoord(tree, args):
    if not isinstance(tree, VS3):
        raise Exception('Texcoord adjustment must be done on a vertex shader (currently)')

    w = 0.5
    if args.adjust_multiply:
        w = args.adjust_multiply
    stereo_const = insert_stereo_declarations(tree, args)

    tmp_reg = tree._find_free_reg('r', VS3)

    for reg in args.adjust_texcoord:
        _adjust_texcoord(tree, reg, args, stereo_const, tmp_reg)

def _disable_texcoord(tree, reg, args, stereo_const, tmp_reg):
    pos_reg = tree._find_free_reg('r', VS3)

    if reg.startswith('dcl_texcoord'):
        reg = find_declaration(tree, reg, 'o').reg
    if reg.startswith('texcoord'):
        reg = find_declaration(tree, 'dcl_%s' % reg, 'o').reg

    disabled = stereo_const.xxxx

    append_inserted_by_comment(tree, 'Texcoord disabled by')
    tree.add_inst('texldl', [tmp_reg, stereo_const.z, tree.def_stereo_sampler])
    separation = tmp_reg.x
    tree.add_inst('if_ne', [separation, -separation]) # Only disable in 3D
    if args.condition:
        tree.add_inst('mov', [tmp_reg.w, args.condition])
        tree.add_inst('if_eq', [tmp_reg.w, stereo_const.x])
    tree.add_inst('mov', [reg, disabled])
    if args.condition:
        tree.add_inst('endif', [])
    tree.add_inst('endif', [])

def disable_texcoord(tree, args):
    if not isinstance(tree, VS3):
        raise Exception('Texcoord adjustment must be done on a vertex shader (currently)')

    stereo_const = insert_stereo_declarations(tree, args)

    tmp_reg = tree._find_free_reg('r', VS3)

    for reg in args.disable_texcoord:
        _disable_texcoord(tree, reg, args, stereo_const, tmp_reg)

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
    stereo_const = insert_stereo_declarations(tree, args)
    tmp_reg = tree._find_free_reg('r', VS3)

    append_inserted_by_comment(tree, 'Shader disabled by')
    if args.disable == '0':
        disabled = stereo_const.xxxx
    if args.disable == '1':
        disabled = stereo_const.yyyy

    tree.add_inst('texldl', [tmp_reg, stereo_const.z, tree.def_stereo_sampler])
    separation = tmp_reg.x
    tree.add_inst('if_ne', [separation, -separation]) # Only disable in 3D
    if args.condition:
        tree.add_inst('mov', [tmp_reg.w, args.condition])
        tree.add_inst('if_eq', [tmp_reg.w, stereo_const.x])
    tree.add_inst('mov', [reg, disabled])
    if args.condition:
        tree.add_inst('endif', [])
    tree.add_inst('endif', [])


def parse_args():
    parser = argparse.ArgumentParser(description = 'nVidia 3D Vision Shaderhacker Tool')
    parser.add_argument('files', nargs='+',
            help='List of shader assembly files to process')
    parser.add_argument('--install', '-i', action='store_true',
            help='Install shaders in ShaderOverride directory')
    parser.add_argument('--force', '-f', action='store_true',
            help='Forcefully overwrite shaders when installing')
    parser.add_argument('--output', '-o', type=argparse.FileType('w'),
            help='Save the shader to a file')

    parser.add_argument('--show-regs', '-r', action='store_true',
            help='Show the registers used in the shader')
    parser.add_argument('--find-free-consts', '--consts', '-c', action='store_true',
            help='Search for unused constants')
    parser.add_argument('--disable', choices=['0', '1'],
            help="Disable a shader, by setting it's output to 0 or 1")
    parser.add_argument('--disable-texcoord', action='append',
            help="Disable a given texcoord in the shader")
    parser.add_argument('--adjust-texcoord', action='append',
            help="Apply the stereo formula to a texcoord")
    parser.add_argument('--adjust-multiply', type=float,
            help="Multiplier for the stereo adjustment. If you notice the broken effect switches eyes try 0.5")
    parser.add_argument('--condition',
            help="Make adjustments conditional on the given register passed in from DX9Settings.ini")
    parser.add_argument('--no-mad', action='store_false', dest='use_mad',
            help="Use mad instruction to make stereo correction more concise")

    parser.add_argument('--adjust-ui-depth', '--ui',
            help='Adjust the output depth of this shader to a percentage of separation passed in from DX9Settings.ini')

    parser.add_argument('--debug-tokeniser', action='store_true',
            help='Dumps the shader broken up into tokens')
    parser.add_argument('--debug-syntax-tree', action='store_true',
            help='Dumps the syntax tree')
    parser.add_argument('--ignore-parse-errors', action='store_true',
            help='Continue with the next file in the event of a parse error')
    return parser.parse_args()

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

    for file in args.files:
        debug('parsing %s...' % file)
        try:
            tree = parse_shader(open(file, 'r', newline=None).read(), args)
        except Exception as e:
            if args.ignore_parse_errors:
                import traceback, time
                traceback.print_exc()
                time.sleep(1)
                continue
            raise
        if hasattr(tree, 'to_shader_model_3'):
            debug('Converting to Shader Model 3...')
            tree.to_shader_model_3()
        if args.debug_syntax_tree:
            debug(repr(tree), end='')
        if args.show_regs or args.find_free_consts or args.adjust_ui_depth or \
                args.disable or args.disable_texcoord or args.adjust_texcoord:
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

        if args.disable:
            disable_shader(tree, args)
        if args.adjust_ui_depth:
            adjust_ui_depth(tree, args)
        if args.disable_texcoord:
            disable_texcoord(tree, args)
        if args.adjust_texcoord:
            adjust_texcoord(tree, args)

        if args.output:
            print(tree, end='', file=args.output)
        if args.install:
            install_shader(tree, file, args)

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

if __name__ == '__main__':
    sys.exit(main())

# vi: et ts=4:sw=4
