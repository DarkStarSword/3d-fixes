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
    pattern = re.compile(r'[ \t]+')

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

    def __str__(self, negate=None):
        if negate is None:
            negate = self.negate
        r = '%s%s%s' % (negate, self.reg, self.absolute) # FIXME: Sync type and num if reg changed
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
        self.shader_start = shader_start
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
        off = 1
        if inst:
            self.insert(self.decl_end, SyntaxTree([NewInstruction(*inst)]))
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

def vs_to_shader_model_3_common(shader, shader_model, extra_fixups = {}):
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

class VS11(VertexShader):
    def to_shader_model_3(self):
        # NOTE: Only very lightly tested!
        vs_to_shader_model_3_common(self, 'vs_1_1', {'mov': fixup_mova})

class VS2(VertexShader):
    def to_shader_model_3(self):
        vs_to_shader_model_3_common(self, 'vs_2_0')

class PS2(PixelShader):
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

        if 't' in self.reg_types:
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

def parse_shader(shader, args):
    tokens = tokenise(shader)
    if args.debug_tokeniser:
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
        debug('Skipping %s - already installed' % file)
        return False

    if show_full_path:
        debug('Installing to %s...' % dest)
    else:
        debug('Installing to %s...' % os.path.relpath(dest, os.curdir))
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
    game_dir = os.path.basename(find_game_dir(file))
    script_dir = os.path.dirname(__file__)
    alias = get_alias(game_dir)
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
        print(str(e))

def insert_stereo_declarations(tree, args, x=0, y=1, z=0.0625, w=0.5):
    if hasattr(tree, 'stereo_const'):
        return tree.stereo_const, 0

    if 's' in tree.reg_types and tree.def_stereo_sampler in tree.reg_types['s']:
        # FIXME: There could be a few reasons for this. For now I assume the
        # shader was already using the sampler, but it's also possible we have
        # simply already added the stereo texture.

        tree.stereo_sampler = tree._find_free_reg('s', None)
        print('WARNING: SHADER ALREADY USES %s! USING %s FOR STEREO SAMPLER INSTEAD!' % \
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

def vanity_comment(args, tree, what):
    a = []
    for arg in sys.argv[1:]:
        if arg not in args.files:
            a.append(arg)
    a.append(tree.filename)

    return [
        "%s DarkStarSword's shadertool.py:" % what,
        '%s %s' % (os.path.basename(sys.argv[0]), ' '.join(a)),
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
        raise Exception('Auto texcoord adjustmost is only applicable to vertex shaders')

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
    return len(tree)

def next_line_pos(tree, position):
    for p in range(position, len(tree)):
        if isinstance(tree[p], NewLine):
            return p + 1
    return len(tree)

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
    print("Scanning shader %s from line %i to %i for %s %s..." % (
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
            # print('scanning %s' % instr)
            if write:
                dest = instr.args[0]
                if is_match(dest):
                    print('Found write to %s on line %s: %s' % (dest, pos_to_line(tree, i), instr))
                    ret.append(Match(i, j, instr))
                    if stop:
                        return ret
            else:
                for arg in instr.args[1:]:
                    if is_match(arg):
                        print('Found read from %s on line %s: %s' % (arg, pos_to_line(tree, i), instr))
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
        raise Exception('Auto texcoord adjustmost is only applicable to vertex shaders')

    # 1. Find output position variable from declarations
    pos_out = find_declaration(tree, 'dcl_position', 'o')

    # 2. Locate where in the shader the output position is set and note which
    #    temporary register was copied to it.
    results = scan_shader(tree, pos_out, write=True)
    if not results:
        print("Couldn't find write to output position register")
        return
    if len(results) > 1:
        # FUTURE: We may be able to handle certain cases of this
        print("Can't autofix a vertex shader writing to output position from multiple instructions")
        return
    (output_line, output_linepos, output_instr) = results[0]
    if output_instr.opcode != 'mov':
        print('Output not using mov instruction: %s' % output_instr)
        return
    temp_reg = output_instr.args[1]
    if not temp_reg.startswith('r'):
        print('Output not moved from a temporary register: %s' % output_instr)
        return

    # 3. Scan upwards to find where the X or W components of the temporary
    #    register was last set.
    results = scan_shader(tree, temp_reg.reg, components='xw', write=True, start=output_line - 1, direction=-1, stop=True)
    if not results:
        print('WARNING: Output set from undefined register!!!?!')
        return
    (temp_reg_line, temp_reg_linepos, temp_reg_instr) = results[0]

    # 4. Scan between the two lines identified in 2 and 3 for any reads of the
    #    temporary register:
    results = scan_shader(tree, temp_reg.reg, write=False, start=temp_reg_line, end=output_line)
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
            print("Line %i: Inserting '%s'" % (pos_to_line(tree, output_line)+1, instr))
            tree.insert_instr(next_line_pos(tree, output_line), instr, 'Inserted by shadertool.py')

        # Actually do the relocation from 5 (FIXME: Move this up, being careful
        # of position offsets):
        line = tree[output_line]
        line.insert(0, CPPStyleComment('// '))
        line.append(WhiteSpace(' '))
        line.append(CPPStyleComment('// Relocated to line %i with shadertool.py' % pos_to_line(tree, relocate_to)))
        print("Line %i: %s" % (pos_to_line(tree, output_line), tree[output_line]))
        tree.insert_instr(prev_line_pos(tree, output_line))
        print("Line %i: Relocating '%s' to here" % (pos_to_line(tree, relocate_to), output_instr))
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
            print('No other reads of temporary variable found, nothing to fix')
            return

    # 9. Insert stereo conversion after new location of move to output position.
    # FIXME: Refactor common code with the adjust_output, etc
    stereo_const, offset = insert_stereo_declarations(tree, args)
    pos = next_line_pos(tree, output_line + offset)
    t = tree._find_free_reg('r', VS3)

    print('Line %i: Applying stereo correction formula to %s' % (pos_to_line(tree, pos), temp_reg.reg))
    pos += insert_vanity_comment(args, tree, pos, "Automatic vertex shader halo fix inserted with")

    pos += tree.insert_instr(pos, NewInstruction('texldl', [t, stereo_const.z, tree.stereo_sampler]))
    separation = t.x; convergence = t.y
    pos += tree.insert_instr(pos, NewInstruction('add', [t.w, temp_reg.w, -convergence]))
    pos += tree.insert_instr(pos, NewInstruction('mad', [temp_reg.x, t.w, separation, temp_reg.x]))
    pos += tree.insert_instr(pos)

    tree.autofixed = True

def add_unity_autofog_VS3(tree):
    try:
        d = find_declaration(tree, 'dcl_fog')
        print('Shader already has a fog output: %s' % d)
        return
    except:
        pass

    if 'o' in tree.reg_types and 'o9' in tree.reg_types['o']:
        print('Shader already uses output o9')
        return

    pos_out = find_declaration(tree, 'dcl_position', 'o')

    results = scan_shader(tree, pos_out, write=True)
    if len(results) != 1:
        print('Output position written from %i instructions (only exactly 1 write currently supported)' % len(results))
        return
    (output_line, output_linepos, output_instr) = results[0]
    if output_instr.opcode != 'mov':
        print('Output not using mov instruction: %s' % output_instr)
        return
    temp_reg = output_instr.args[1]
    if not temp_reg.startswith('r'):
        print('Output not moved from a temporary register: %s' % output_instr)
        return

    fog_output = NewInstruction('mov', ['o9', temp_reg.z])
    tree.insert_instr(next_line_pos(tree, output_line), fog_output, 'Inserted by shadertool.py to match Unity autofog')
    decl = NewInstruction('dcl_fog', ['o9'])
    tree.insert_instr(next_line_pos(tree, tree.shader_start), decl, 'Inserted by shadertool.py to match Unity autofog')

def add_unity_autofog(tree):
    '''
    Adds instructions to a shader to match those Unity automatically adds for
    fog. Used by extract_unity_shaders.py to construct fog variants of shaders.
    '''
    if isinstance(tree, VS3):
        return add_unity_autofog_VS3(tree)

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
                print('%s appears to already contain headers' % file)
                return tree

    crc = shaderutil.get_filename_crc(file)
    try:
        headers = index[crc]
    except:
        print('%s not found in header index' % crc)
        return tree
    headers = [ (CPPStyleComment(x), NewLine('\n')) for x in headers.split('\n') ]
    headers = type(tree)(itertools.chain(*headers), None)
    headers.shader_start = len(headers) + tree.shader_start
    headers.append(NewLine('\n'))
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
    print()
    print()
    print('!' * 79)
    print('!' * 12 + ' Please add the following lines to the DX9Settings.ini ' + '!' * 12)
    print('!' * 79)
    print()
    for section in dx9settings_ini:
        print('[%s]' % section)
        for line in dx9settings_ini[section]:
            if isinstance(line, tuple):
                print('%s = %s' % line)
            else:
                print(line)
        print()

def parse_args():
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
    parser.add_argument('--only-autofixed', action='store_true',
            help="Installation type operations only act on shaders that were successfully autofixed with --auto-fix-vertex-halo")

    parser.add_argument('--add-unity-autofog', action='store_true',
            help="Add instructions to the shader to support fog, like Unity does (used by extract_unity_shaders.py)")

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
    args = parser.parse_args()

    if args.to_git:
        if not args.output and not args.install and not args.install_to and not args.to_git:
            args.auto_convert = False

    if args.lookup_header_json:
        args.lookup_header_json = json.load(args.lookup_header_json)
        if not args.output and not args.install and not args.install_to and not args.to_git:
            args.in_place = True
            args.auto_convert = False

    if args.restore_original:
        args.auto_convert = False

    if args.add_unity_autofog:
        args.auto_convert = False

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
                args.add_unity_autofog

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
        if args.restore_original:
            print('Restoring %s...' % file)
            restore_original_shader(file)
            continue

        real_file = file
        if args.original:
            file = find_original_shader(file)

        debug('parsing %s...' % file)
        try:
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
            debug('Converting to Shader Model 3...')
            tree.to_shader_model_3()
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

        if args.add_unity_autofog:
            add_unity_autofog(tree)
        if args.disable:
            disable_shader(tree, args)
        if args.auto_adjust_texcoords:
            auto_adjust_texcoords(tree, args)
        tree.autofixed = False
        if args.auto_fix_vertex_halo:
            auto_fix_vertex_halo(tree, args)
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
