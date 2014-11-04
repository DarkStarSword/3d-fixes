#!/usr/bin/env python3

import sys, os, re, math
import json, hashlib, collections

# Tokeniser loosely based on
# https://docs.python.org/3.4/library/re.html#writing-a-tokenizer

class Token(str): pass

class Strip(object): pass # Removed during tokenisation
class Ignore(object): pass # Ignored when looking for identifiers

class CPPStyleComment(Token, Strip):
    pattern = r'\/\/.*$'

def strip_quotes(s):
    if s[0] == s[-1] == '"':
        return s[1:-1].strip()
    return s.strip()

class String(Token):
    pattern = r'"[^"]*"'

class CurlyLeft(Token):
    pattern = r'{'

class CurlyRight(Token):
    pattern = r'}'

class WhiteSpace(Token, Ignore):
    pattern = r'[ \t]+'

class NewLine(WhiteSpace, Token):
    pattern = r'\n'

class Identifier(Token):
    pattern = r'[a-zA-Z0-9\[\]_]+'

class Other(Token):
    pattern = r'.'

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

def tokenise(input):
    token_dict = {token.__name__: token for token in tokens}
    tok_regex = r'|'.join('(?P<%s>%s)' % (token.__name__, token.pattern) for token in tokens)
    for mo in re.finditer(tok_regex, input, re.MULTILINE):
        kind = token_dict[mo.lastgroup]
        value = kind(mo.group(mo.lastgroup))
        if not isinstance(kind, Strip):
            yield value

def curly_scope(old_tree):
    tree = Tree()
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

class Tree(list):
    def __str__(self):
        if len(self) == 0:
            return '{}'
        return '{%s}' % stringify(self)

class NamedTree(Keyword, Tree):
    def parse(self, tokens, parent):
        self.orig_name = next_interesting(tokens)
        self.name = strip_quotes(self.orig_name)
        Tree.__init__(self, parse_keywords(next_interesting(tokens), parent=self))

    def header(self):
        return '%s %s {' % (Keyword.__str__(self), self.orig_name)

    def __str__(self):
        return '%s\n%s\n}' % (self.header(), stringify_nl(self))

class UnnamedTree(Keyword, Tree):
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

        Tree.__init__(self, parse_keywords(next_interesting(tokens), parent=self))

    def header(self):
        return '%s %i/%i {' % (Keyword.__str__(self), self.counter, self.parent_counter)

    def __str__(self):
        return '%s\n%s\n}' % (self.header(), stringify_nl(self))

class StringifyTree(Keyword):
    def parse(self, tokens, parent):
        inner = next_interesting(tokens)
        self.child = stringify(inner)

    def __str__(self):
        return '%s {%s}' % (Keyword.__str__(self), self.child)

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
        return '%s %s' % (Keyword.__str__(self), self.line.strip())

class Keywords(Keyword, set):
    def parse(self, tokens, parent):
        set.__init__(self, map(strip_quotes, map(str, ignore_whitespace(next_interesting(tokens)))))

    def __str__(self):
        kws = ['"%s"' % x for x in sorted(self)]
        return '%s { %s }' % (Keyword.__str__(self), ' '.join(kws))

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

def parse_keywords(tree, parent=None, filename=None):
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
            parent.shader_asm = strip_quotes(token)
            # Index shaders by assembly:
            if token not in shader_index:
                shader_index[token] = []
            shader_index[token].append(parent)
            shader_list.append(parent)
            continue

        if not isinstance(token, Identifier):
            raise SyntaxError('Expected Identifier, found: %s' % repr(token))

        if token not in keywords:
            raise SyntaxError('Unrecognised keyword: %s (maybe just need to add this to list of known keywords?)' % token)

        item = keywords[token](token, tokens, parent)
        if filename is not None:
            item.filename = filename
        ret.append(item)

        if parent is not None:
            if token not in parent.keywords:
                parent.keywords[token] = []
            parent.keywords[token].append(item)

    return ret

def get_parents(sub_program):
    Shader = collections.namedtuple('Shader', ['sub_program', 'program', 'shader_pass', 'sub_shader', 'shader'])

    program = sub_program.parent
    shader_pass = program.parent
    sub_shader = shader_pass.parent
    shader = sub_shader.parent

    assert(sub_program.keyword == 'SubProgram')
    assert(program.keyword == 'Program')
    assert(shader_pass.keyword == 'Pass')
    assert(sub_shader.keyword == 'SubShader')
    assert(shader.keyword == 'Shader')

    return Shader(sub_program, program, shader_pass, sub_shader, shader)

def export_filename(sub_program):
    (sub_program, program, shader_pass, sub_shader, shader) = get_parents(sub_program)

    ret = []

    ret.append('Shaders')
    ret.append(sub_program.name.strip())

    # basename, ext = os.path.splitext(shader.filename)
    # ret.append('%s - %s' % (basename, shader.name))
    ret.append(shader.name)

    ret.append('SubShader %d' % sub_shader.counter)

    if 'Name' in shader_pass.keywords:
        pass_name = strip_quotes(shader_pass.keywords['Name'][0].line.strip())
        ret.append('Pass %d - %s' % (shader_pass.counter, pass_name))
    else:
        ret.append('Pass %d' % shader_pass.counter)

    ret.append(program.name)

    if 'Keywords' in sub_program.keywords:
        assert(len(sub_program.keywords['Keywords']) == 1)
        keywords = ' '.join(sorted(sub_program.keywords['Keywords'][0]))
        ret.append(keywords)

    return [x.replace('/', '_') for x in ret]

def export_filename_combined(sub_programs):
    shaders = list(map(get_parents, sub_programs))

    # Different sub programs have different assembly languages and should not match:
    assert(all([ x.sub_program.name == shaders[0].sub_program.name for x in shaders]))

    # Filenames potentially could match:
    # assert(all([ x.shader.filename == shaders[0].shader.filename for x in shaders]))

    # Should be identical because we explicitly filtered on this:
    assert(all([ x.shader.name == shaders[0].shader.name for x in shaders]))

    # vertex & pixel shaders embed different identifiers in the assembly, so should not match:
    assert(all([ x.program.name == shaders[0].program.name for x in shaders]))

    ret = []

    ret.append('Shaders')
    ret.append(shaders[0].sub_program.name.strip())

    # basename, ext = os.path.splitext(shaders[0].shader.filename)
    # ret.append('%s - %s' % (basename, shaders[0].shader.name))
    ret.append(shaders[0].shader.name)

    subshaders = set([ x.sub_shader.counter for x in shaders ])
    ret.append('SubShader %s' % '+'.join(map(str, sorted(subshaders))))

    def pass_name(shader):
        if 'Name' in shader.shader_pass.keywords:
            return strip_quotes(shader.shader_pass.keywords['Name'][0].line.strip())
    passes = set([ x.shader_pass.counter for x in shaders ])
    names = set(filter(None, map(pass_name, shaders)))
    component = 'Pass %s' % '+'.join(map(str, sorted(passes)))
    if names:
        component += ' - ' + ' '.join(sorted(names))
    ret.append(component)

    ret.append(shaders[0].program.name)

    def keywords(shader):
        if 'Keywords' in shader.sub_program.keywords:
            assert(len(shader.sub_program.keywords['Keywords']) == 1)
            return shader.sub_program.keywords['Keywords'][0]
        return set()
    kw = set()
    kw.update(*map(keywords, shaders))
    if kw:
        ret.append(' '.join(sorted(kw)))

    return [x.replace('/', '_') for x in ret]

def _collect_headers(tree):
    headers = []
    indent = 0
    if tree.parent is not None:
        (headers, indent) = (_collect_headers(tree.parent))
    else:
        headers.append('Unity headers extracted from %s' % tree.filename)
    headers.append('  ' * indent + tree.header())
    for item in tree:
        if isinstance(item, Tree):
            # Don't get headers for anything else in this file
            continue
        items = str(item).split('\n')
        items = [ '  ' * (indent + 1) + x for x in items ]
        headers.extend(items)
    return (headers, indent + 1)

def collect_headers(tree):
    (headers, nest) = _collect_headers(tree)
    for indent in reversed(range(nest)):
        headers.append('  ' * indent + '}')
    return headers

def _combine_similar_headers(ret, headers):
    head = [ len(x) > 0 and x[0] or '' for x in headers ] # headers on this line
    next = [ len(x) > 1 and x[1] or '' for x in headers ] # headers on next line

    bmplen = math.ceil(len(headers) / 4)

    # Simple case - lines from all headers match:
    if all([ x == head[0] for x in head ]):
        [ len(x) and x.pop(0) for x in headers ]
        ret.append('%s  %s' % (' ' * bmplen, head[0]))
        return

    # At least one header varies, get the first word of each header:
    kh = [ x.strip().split(' ', 1)[0] for x in head ] # Keywords on this line
    kn = [ x.strip().split(' ', 1)[0] for x in next ] # Keywords on next line

    # Find any singular headers and flush them immediately:
    for i, k in enumerate(kh):
        if not head[i] or k == '}' or head[i].endswith('{'):
            continue
        if kh.count(k) + kn.count(k) == 1:
            # Only one occurrence of this keyword, flush it out now
            headers[i].pop(0)
            ret.append('%.*x: %s' % (bmplen, 1<<i, head[i]))
            return

    # Could do more here, but let's see if it's necessary in practice

    # Dump any ungrouped headers:
    tmp = {}
    for i, k in enumerate(kh):
        if not head[i]:
            continue
        headers[i].pop(0)
        tmp.setdefault(head[i], 0)
        tmp[head[i]] |= 1 << i
    for (h, bmp) in sorted(tmp.items()):
        ret.append('%.*x: %s' % (bmplen, bmp, h))

def combine_similar_headers(trees):
    headers = list(map(collect_headers, trees))
    ret = []
    while any(headers):
        _combine_similar_headers(ret, headers)
    return ret

def commentify(headers):
    return '\n'.join([ '// %s' % x for x in headers ])

def mkdir_recursive(components):
    path = os.curdir
    while components:
        path = os.path.join(path, components.pop(0))
        if os.path.isdir(path):
            continue
        os.mkdir(path)

def add_vanity_tag(headers):
    if headers[-1] != '':
        headers.append('')
    headers.append("Headers extracted with DarkStarSword's extract_unity_shaders.py")
    headers.append("https://raw.githubusercontent.com/DarkStarSword/3d-fixes/master/extract_unity_shaders.py")

def _export_shader(shader_asm, headers, path_components):
    mkdir_recursive(path_components[:-1])
    dest = os.path.join(os.curdir, *path_components)
    print('Extracting %s.txt...' % dest)
    with open('%s.txt' % dest, 'w') as f:
        f.write(commentify(headers))
        f.write('\n\n')
        f.write(shader_asm)
    with open('%s.raw' % dest, 'w') as f: # XXX: May need to check line endings to get the same CRC as Helix?
        f.write(shader_asm)

def export_shader(sub_program):
    headers = collect_headers(sub_program)
    add_vanity_tag(headers)
    path_components = export_filename(sub_program)
    return _export_shader(sub_program.shader_asm, headers, path_components)

def shader_name(tree):
    while tree.parent is not None:
        tree = tree.parent
    return tree.name

def dedupe_shaders(shader_list):
    asm = shader_list[0].shader_asm
    assert(all([ x.shader_asm == asm for x in shader_list]))

    headers = []
    shaders = sorted(set(map(shader_name, shader_list)))
    headers.append('Matched %i variants of %i shaders: %s' %
            (len(shader_list), len(shaders), ', '.join(shaders)))
    headers.append('')
    for shader in shaders:
        similar_shaders = filter(lambda x: shader_name(x) == shader, shader_list)
        headers.extend(combine_similar_headers(similar_shaders))
        headers.append('')
    add_vanity_tag(headers)
    # print(commentify(headers))

    for shader in shaders:
        similar_shaders = filter(lambda x: shader_name(x) == shader, shader_list)
        path_components = export_filename_combined(similar_shaders)
        _export_shader(asm, headers, path_components)

def main():
    global shader_list
    processed = set()

    for filename in sys.argv[1:]:
        shader_list = []
        print('Parsing %s...' % filename)
        data = open(filename, 'rb').read()
        digest = hashlib.sha1(data).digest()
        if digest in processed:
            continue
        processed.add(digest)
        tree = list(tokenise(data.decode('ascii'))) # I don't know what encoding it uses
        tree = curly_scope(tree)
        tree = parse_keywords(tree, filename=os.path.basename(filename))

    for shaders in shader_index.values():
        if len(shaders) == 1:
            export_shader(shaders[0])
        else:
            # print('-'*79)
            dedupe_shaders(shaders)

if __name__ == '__main__':
    sys.exit(main())

# vi: sw=4:ts=4:expandtab
