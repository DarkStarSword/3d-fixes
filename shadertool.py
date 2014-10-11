#!/usr/bin/env python3

import sys, os, re

reg_names = {
    'c': 'Referenced Constants',
    'r': 'Temporary',
    's': 'Samplers',
    'v': 'Inputs',
    'o': 'Outputs',
    'oC': 'Output Colour',
    'oPos': 'Output Position (shader model < 3)',
    'oT': 'Output Texcoord (shader model < 3)',
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
    pattern = re.compile(r'[a-zA-Z_\-][a-zA-Z_0-9\.]*')

class Comma(Token):
    pattern = re.compile(r',')

class Float(Token, Number):
    pattern = re.compile(r'-?[0-9]*\.[0-9]*(e-?[0-9]+)?')

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
        (?:
            \.
            (?P<swizzle>[abcdxyzw]{1,4})
        )?
    ''', re.VERBOSE)
    def __new__(cls, s):
        match = cls.pattern.fullmatch(s)
        if match is None:
            raise SyntaxError('Expected register, found %s' % s)
        ret = str.__new__(cls, s)
        ret.negate = match.group('negate') or ''
        ret.absolute = match.group('absolute') or ''
        ret.type = match.group('type')
        ret.num = match.group('num')
        ret.reg = ret.type + ret.num
        if ret.num:
            ret.num = int(ret.num)
        ret.swizzle = match.group('swizzle')
        return ret

    def __lt__(self, other):
        if self.num is not None:
            return self.num < other.num
        return str.__lt__(self, other)

    def __str__(self):
        r = '%s%s%s' % (self.negate, self.reg, self.absolute) # FIXME: Sync type and num if reg changed
        if self.swizzle:
            r += '.%s' % self.swizzle
        return r

class Instruction(SyntaxTree):
    def is_declaration(self):
        return self.opcode == 'def' or self.opcode.startswith('dcl_') or self.opcode in sections

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
            if tree.opcode.startswith('dcl_'):
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
            if tree.opcode == 'def':
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
                if inst.is_declaration():
                    if not in_dcl:
                        raise SyntaxError("Bad shader: Mixed declarations with code: %s" % inst)
                elif in_dcl:
                    self.decl_end = lineno
                    in_dcl = False
                t.append(inst)
            newtree.append(t)
        SyntaxTree.__init__(self, newtree)

    def insert_decl(self, inst=None):
        if inst is not None:
            self.insert(self.decl_end, SyntaxTree([inst]))
            self.decl_end += 1
        self.insert(self.decl_end, NewLine('\n'))
        self.decl_end += 1

    def analyse_regs(self, verbose=False):
        def pr_verbose(*args, **kwargs):
            if verbose:
                debug(*args, **kwargs)

        self.local_consts = RegSet()
        self.declared = RegSet()
        self.reg_types = {}
        for (inst, parent, idx) in self.iter_all():
            if not isinstance(inst, Instruction):
                continue
            if inst.opcode == 'def':
                self.local_consts.add(inst.args[0])
                continue
            if inst.opcode.startswith('dcl_'):
                self.declared.add(inst.args[0])
                continue
            for arg in inst.args:
                if arg.type not in self.reg_types:
                    self.reg_types[arg.type] = RegSet()
                self.reg_types[arg.type].add(arg)

        self.global_consts = self.unref_consts = RegSet()
        if 'c' in self.reg_types:
            self.global_consts = self.reg_types['c'].difference(self.local_consts)
            self.unref_consts = self.local_consts.difference(self.reg_types['c'])

        pr_verbose('Local constants: %s' % ', '.join(sorted(self.local_consts)))
        pr_verbose('Global constants: %s' % ', '.join(sorted(self.global_consts)))
        pr_verbose('Unused local constants: %s' % ', '.join(sorted(self.unref_consts)))
        pr_verbose('self.Declared: %s' % ', '.join(sorted(self.declared)))
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

    def do_replacements(self, regs, insts, callbacks):
        for (node, parent, idx) in self.iter_all():
            if isinstance(node, Register):
                if node.reg in regs:
                    node.reg = regs[node.reg] # FIXME: Update reg.type
            if isinstance(node, Instruction):
                if node.opcode in insts:
                    parent[idx] = insts[node.opcode]
                if node.opcode in callbacks:
                    callbacks[node.opcode](self, node, parent, idx)

    def discard_if_unused(self, regs, reason = 'unused'):
        self.analyse_regs()
        discard = self.unref_consts.intersection(RegSet(regs))
        if not discard:
            return
        for (node, parent, idx) in self.iter_all():
            if isinstance(node, Instruction) and node.opcode == 'def' and node.args[0] in discard:
                parent[idx] = CPPStyleComment('// Discarded %s constant %s' % (reason, node.args[0]))

def fixup_sincos(tree, node, parent, idx):
    parent[idx] = NewInstruction('sincos', (node.args[0], node.args[1]))
    tree.discard_if_unused((node.args[2], node.args[3]), 'sincos')

class VS3(ShaderBlock):
    max_regs = { # http://msdn.microsoft.com/en-us/library/windows/desktop/bb172963(v=vs.85).aspx
        'c': 256,
        'o': 12,
        'r': 32,
        's': 4,
        'v': 16,
    }

class PS3(ShaderBlock):
    max_regs = { # http://msdn.microsoft.com/en-us/library/windows/desktop/bb172920(v=vs.85).aspx
        'c': 224,
        'r': 32,
        's': 16,
        'v': 12,
    }

class VS2(ShaderBlock):
    def to_shader_model_3(self):
        self.analyse_regs()
        self.insert_decl()
        replace_regs = {}

        for reg in sorted(self.reg_types['oT']):
            opcode = 'dcl_texcoord'
            if reg.num:
                opcode = 'dcl_texcoord%d' % reg.num
            out = self._find_free_reg('o', VS3)
            self.insert_decl(NewInstruction(opcode, [out]))
            replace_regs[reg.reg] = out

        out = self._find_free_reg('o', VS3)
        self.insert_decl(NewInstruction('dcl_position', [out]))
        replace_regs['oPos'] = out

        self.insert_decl()

        self.do_replacements(replace_regs, {'vs_2_0': 'vs_3_0'}, {'sincos': fixup_sincos})

class PS2(ShaderBlock):
    def to_shader_model_3(self):
        self.analyse_regs()
        self.insert_decl()
        replace_regs = {}

        for reg in sorted(self.reg_types['t']):
            opcode = 'dcl_texcoord'
            if reg.num:
                opcode = 'dcl_texcoord%d' % reg.num
            out = self._find_free_reg('v', PS3)
            self.insert_decl(NewInstruction(opcode, [out]))
            replace_regs[reg.reg] = out

        self.insert_decl()

        self.do_replacements(replace_regs, {'ps_2_0': 'ps_3_0'}, {'sincos': fixup_sincos})

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

def parse_shader(shader):
    tokens = tokenise(shader)
    # for token in tokens:
    #     debug('%s: %s' % (token.__class__.__name__, repr(str(token))))
    tree = SyntaxTree(tokens)
    tree = SyntaxTree.split_newlines(tree)
    tree = process_sections(tree)
    if hasattr(tree, 'to_shader_model_3'): # TODO: Add optparse
        tree.to_shader_model_3()
    # print(repr(tree), end='') # TODO: Add optparse
    # tree.analyse_regs(True) # TODO: Add optparse
    print(tree, end='')

def main():
    for file in sys.argv[1:]:
        parse_shader(open(file, 'r', newline=None).read())

if __name__ == '__main__':
    sys.exit(main())

# vi: et ts=4:sw=4
