#!/usr/bin/env python3

import sys, os, re
import json

# See also - an alternative way to write a tokeniser (maybe I'll switch):
# https://docs.python.org/3.4/library/re.html#writing-a-tokenizer

class Token(object):
    def __init__(self, string):
        match = self.pattern.match(string)
        if match is None:
            raise ValueError()
        self.string = match.string[:match.end()]

    def __repr__(self):
        return repr(self.string)

    def __str__(self):
        return self.string

    def __len__(self):
        return len(self.string)

class Strip(object): pass # Removed during tokenisation
class Ignore(object): pass # Ignored when looking for identifiers

class CPPStyleComment(Token, Strip):
    pattern = re.compile(r'\/\/.*$', re.MULTILINE)

class String(Token):
    pattern = re.compile(r'"[^"]*"', re.MULTILINE)

    def __repr__(self):
        return repr(self.string[1:-1])

    def __str__(self):
        return self.string[1:-1]

class CurlyLeft(Token):
    pattern = re.compile(r'{')

class CurlyRight(Token):
    pattern = re.compile(r'}')

class WhiteSpace(Token, Ignore):
    pattern = re.compile(r'\s')

class NewLine(WhiteSpace, Token):
    pattern = re.compile(r'\n')

class Identifier(Token):
    pattern = re.compile(r'[a-zA-Z0-9\[\]_]+')

class Other(Token):
    pattern = re.compile(r'.')

tokens = [
    CPPStyleComment,
    String,
    CurlyLeft,
    CurlyRight,
    NewLine,
    WhiteSpace,
    Identifier,
    Other,
]

def parse_token(input):
    for t in tokens:
        try:
            token = t(input)
        except ValueError:
            continue
        if token is not None:
            return (token, input[len(token):])
    try:
        msg = input.split('\n')[0]
    except:
        msg = input
    raise SyntaxError(repr(msg))

def tokenise(input):
    result = []
    while input:
        (token, input) = parse_token(input)
        # print(repr(token))
        if not isinstance(token, Strip):
            result.append(token)
    return result

def curly_scope(old_tree):
    tree = []
    while old_tree:
        token = old_tree.pop(0)
        if isinstance(token, CurlyRight):
            return tree
        if isinstance(token, CurlyLeft):
            tree.append(curly_scope(old_tree))
        else:
            tree.append(token)
    return tree

def ignore_whitespace(tree):
    for token in tree:
        if isinstance(token, Ignore):
            continue
        yield token

def next_interesting(tree):
    while True:
        r = next(tree)
        if isinstance(r, Ignore):
            continue
        return r

class Keyword(object):
    def __init__(self, keyword, tokens, parent):
        self.keyword = keyword
        self.parent = parent
        return self.parse(tokens, parent)

    def __str__(self):
        return self.keyword

def stringify(tree):
    # Needed because Tokens aren't subclassed from str. Tokens aren't
    # subclassed from str because doing so means we can't use __str__ to
    # transform "blah" into blah (Could probably fix this by transforming it in
    # __new__ instead, but I need to fix the tokeniser).
    return ''.join(map(str, tree))

def stringify_nl(tree):
    return '\n'.join(map(str, tree))

class NamedTree(Keyword):
    def parse(self, tokens, parent):
        self.name = str(next_interesting(tokens))
        self.child = parse_keywords(next_interesting(tokens), self)

    def __str__(self):
        return '%s "%s" {\n%s\n}' % (Keyword.__str__(self), self.name, stringify_nl(self.child))

class UnnamedTree(Keyword):
    @property
    def parent_counter_attr(self):
        return '%s_counter' % self.keyword

    @property
    def parent_counter(self):
        return getattr(self.parent, self.parent_counter_attr, 0)

    @parent_counter.setter
    def parent_counter(self, val):
        return setattr(self.parent, self.parent_counter_attr, val)

    def parse(self, tokens, parent):
        self.parent_counter += 1
        self.counter = self.parent_counter

        self.child = parse_keywords(next_interesting(tokens), self)

    def __str__(self):
        return '%s %i/%i {\n%s\n}' % (Keyword.__str__(self), self.counter, self.parent_counter, stringify_nl(self.child))

class StringifyTree(Keyword):
    def parse(self, tokens, parent):
        inner = next_interesting(tokens)
        self.child = stringify(inner)

    def __str__(self):
        return '%s { %s }' % (Keyword.__str__(self), self.child)

class StringifyLine(Keyword):
    def parse(self, tokens, parent):
        t = []
        while True:
            token = next(tokens)
            if isinstance(token, NewLine):
                break
            t.append(token)
        self.line = stringify(t)

    def __str__(self):
        return '%s %s' % (Keyword.__str__(self), self.line)

class Keywords(Keyword, set):
    def parse(self, tokens, parent):
        set.__init__(self, map(str, ignore_whitespace(next_interesting(tokens))))

    def __str__(self):
        return '%s { %s }' % (Keyword.__str__(self), ' '.join(self))

# The syntax in this file format is very inconsistent, making it difficult to
# write a generic parser that handles everything properly unless it knows what
# type all the keywords are.
keywords = {
        'Shader': NamedTree,
        'Program': NamedTree,
        'SubProgram': NamedTree,

        'SubShader': UnnamedTree,
        'Pass': UnnamedTree,

        'Keywords': Keywords,

        # Treat anything we don't care about parsing properly as a string. I
        # could probably handle this in a better way by treating all unknowns
        # as something to stringify, but I wanted to make sure I didn't miss
        # anything.

        # keyword { string }:
        'Properties': StringifyTree,
        'Fog': StringifyTree,
        'Tags': StringifyTree,
        'Material': StringifyTree,
        'BindChannels': StringifyTree,

        # or just 'keyword string':
        'LOD': StringifyLine,
        'Name': StringifyLine,
        'Bind': StringifyLine,
        'Matrix': StringifyLine,
        'Vector': StringifyLine,
        'ConstBuffer': StringifyLine,
        'BindCB': StringifyLine,
        'SetTexture': StringifyLine,
        'ZWrite': StringifyLine,
        'Blend': StringifyLine,
        'Fallback': StringifyLine,
        'AlphaTest': StringifyLine,
        'ColorMask': StringifyLine,
        'Float': StringifyLine,
        'Lighting': StringifyLine,
        'SeparateSpecular': StringifyLine,
        'Cull': StringifyLine,
        'AlphaToMask': StringifyLine,
        'Offset': StringifyLine,
        'Dependency': StringifyLine,
        'ZTest': StringifyLine,
        'ColorMaterial': StringifyLine,
        'UsePass': StringifyLine,
}

shader_index = {}
shader_list = []

def parse_keywords(tree, parent=None):
    ret = []
    tokens = iter(tree)
    if parent is not None and not hasattr(parent, 'keywords'):
        parent.keywords = {}
    while True:
        try:
            token = next_interesting(tokens)
        except StopIteration:
            break

        if isinstance(token, String):
            parent.shader_asm = token
            # Index shaders by assembly:
            if token not in shader_index:
                shader_index[token] = []
            shader_index[token].append(parent)
            shader_list.append(parent)
            continue

        if not isinstance(token, Identifier):
            raise SyntaxError('Expected Identifier, found: %s' % repr(token))

        token = str(token) # FIXME: Got to be a cleaner way, this is necessary because Tokens aren't subclassed from str
        if token not in keywords:
            raise SyntaxError('Unrecognised keyword: %s (maybe just need to add this to list of known keywords?)' % token)

        item = keywords[token](token, tokens, parent)
        ret.append(item)

        if parent is not None:
            if token not in parent.keywords:
                parent.keywords[token] = []
            parent.keywords[token].append(item)

    return ret

def export_shaders(shader_list):
    for sub_program in shader_list:
        program = sub_program.parent
        shader_pass = program.parent
        sub_shader = shader_pass.parent
        shader = sub_shader.parent

        assert(sub_program.keyword == 'SubProgram')
        assert(program.keyword == 'Program')
        assert(shader_pass.keyword == 'Pass')
        assert(sub_shader.keyword == 'SubShader')
        assert(shader.keyword == 'Shader')

        keywords = ''
        if 'Keywords' in sub_program.keywords:
            assert(len(sub_program.keywords['Keywords']) == 1)
            keywords = '.(%s)' % ' '.join(sub_program.keywords['Keywords'][0])

        print('{}.SubShader[{}].Pass[{}].{}.{}{}'.format(shader.name,
            sub_shader.counter, shader_pass.counter, program.name,
            sub_program.name.strip(), keywords))

def main():
    for file in sys.argv[1:]:
        print('Parsing %s...' % file)
        tree = tokenise(open(file, 'r').read())
        tree = curly_scope(tree)
        tree = parse_keywords(tree)
        # print('\n'.join(map(str, tree)))

        # print(shader_index)
        export_shaders(shader_list)

if __name__ == '__main__':
    sys.exit(main())
