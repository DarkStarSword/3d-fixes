#!/usr/bin/env python3

import sys, os, re, math
import json, hashlib, collections

shader_idx_filename = 'ShaderHeaders.json'

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
        if not isinstance(value, Strip):
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

        # Anything else will be processed by StringifyLine
}

shader_index = {}
shader_list = []
crc_list = {}
crc_headers = {}

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
            if token in shader_index:
                # Minimise calls to shaderasm.exe
                parent.crc = shader_index[token][0].crc
            else:
                shader_index[token] = []
                add_shader_crc(parent)
                if parent.crc:
                    if parent.crc in crc_list:
                        print('%s WARNING: CRC32 COLLISION DETECTED: %.8X %s' % ('-'*17, parent.crc, '-'*17))
                        crc_list[parent.crc].append(parent)
                        print('\n'.join([ \
                                os.path.sep.join(export_filename_combined_long([get_parents(x)], None)) \
                                for x in crc_list[parent.crc] ]))
                        print('%s OVERRIDING THESE SHADERS MAY BE DANGEROUS %s' % ('-'*18, '-'*18))
                        print()
                    else:
                        crc_list[parent.crc] = [parent]
            shader_index[token].append(parent)
            shader_list.append(parent)
            continue

        if not isinstance(token, Identifier):
            raise SyntaxError('Expected Identifier, found: %s' % repr(token))

        if token in keywords:
            item = keywords[token](token, tokens, parent)
        else:
            # I used to be strict and fail on any unrecognised keywords, but I
            # kept running into more so now I just stringify them:
            item = StringifyLine(token, tokens, parent)

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

abbreviations = (
    ('DIRECTIONAL', 'DIR'),
    ('COOKIE', 'CK'),
    ('POINT', 'PT'),
    ('SHADOWS', 'SHDW'),
    ('SOFT', 'SFT'),
    ('CUBE', 'CBE'),
    ('SCREEN', 'SCN'),
    ('NATIVE', 'NTV'),
    ('DEPTH', 'DEP'),
    ('OFF', 'OF'),
    ('SPOT', 'SPT'),
    ('SUNSHINE', 'SUN'),
    ('FILTER', 'FLT'),
    ('HARD', 'HRD'),
    ('SOFT', 'SFT'),
    ('DISABLED', 'DIS'),
)

def abbreviate(word):
    for a in abbreviations:
        word = word.replace(*a)
    return word


def compress_keywords(keywords):
    keywords = map(abbreviate, keywords)
    split = [x.rsplit('_', 1) for x in keywords]

    ret = []

    ret.extend([x[0] for x in split if len(x) == 1])
    multiword = [x for x in split if len(x) > 1]
    for word in set([x[0] for x in multiword]):
        remaining = [x[1] for x in multiword if x[0] == word]
        if len(remaining) == 1:
            ret.append('%s_%s' % (word, ''.join(remaining)))
        else:
            ret.append('%s_(%s)' % (word, '+'.join(remaining)))
    return ' '.join(sorted(ret))

def export_filename_combined_long(shaders, args):
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

    if args and args.filename_crc and shaders[0].sub_program.crc:
        ret.append('%.8X' % shaders[0].sub_program.crc)
    else:
        def keywords(shader):
            if 'Keywords' in shader.sub_program.keywords:
                assert(len(shader.sub_program.keywords['Keywords']) == 1)
                return shader.sub_program.keywords['Keywords'][0]
            return set()
        kw = set()
        kw.update(*map(keywords, shaders))
        if kw:
            ret.append(compress_keywords(kw))

    return ret

def export_filename_combined_short(shader, args):
    if not shader.sub_program.crc:
        return None
    return (
        'ShaderCRCs',
        shader.shader.name,
        shader.program.name,
        '%.8X' % shader.sub_program.crc,
    )

def export_filename_combined(sub_programs, args):
    shaders = list(map(get_parents, sub_programs))

    # Different sub programs have different assembly languages and should not match:
    assert(all([ x.sub_program.name == shaders[0].sub_program.name for x in shaders]))

    # Filenames potentially could differ:
    # assert(all([ x.shader.filename == shaders[0].shader.filename for x in shaders]))

    # Should be identical because we explicitly filtered on this:
    assert(all([ x.shader.name == shaders[0].shader.name for x in shaders]))

    # vertex & pixel shaders embed different identifiers in the assembly, so should not match:
    assert(all([ x.program.name == shaders[0].program.name for x in shaders]))

    if args.flatten:
        ret = export_filename_combined_short(shaders[0], args)
    else:
        ret = export_filename_combined_long(shaders, args)
    if ret is not None:
        return [x.replace('/', '_') for x in ret]
    return None

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

    # Find all future headers:
    future = set()
    for h in headers:
        future.update(h[1:])

    bmplen = math.ceil(len(headers) / 4)

    # Simple case - lines from all headers match:
    if all([ x == head[0] for x in head ]):
        [ len(x) and x.pop(0) for x in headers ]
        ret.append('%s  %s' % (' ' * bmplen, head[0]))
        return

    # Don't dump out any headers that are also found on a future line:
    for i,h in enumerate(head):
        if h in future:
            head[i] = None

    # Could also delay lines with keywords appearing on a future line in the
    # same scope - be careful of 'Tags' keyword appearing in multiple scopes!
    # For now let's see if this is sufficient.

    if not any(head):
        # Avoid potential live lock - certain patterns of headers could
        # potentially cause each header stream to block waiting on the other
        # streams to flush to a matching line.
        # If all streams are blocked, force flushing out the current lines:
        head = [ len(x) > 0 and x[0] or '' for x in headers ]

    # Dump any ungrouped headers:
    tmp = {}
    for i,h in enumerate(head):
        if not h:
            continue
        headers[i].pop(0)
        tmp.setdefault(h, 0)
        tmp[h] |= 1 << i
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

def indent_like_helix(assembly):
    return '\n'.join([ '%s%s' % (' '*4, x) for x in assembly.split('\n') ]) + '\n'

def mkdir_recursive(components):
    path = os.curdir
    while components:
        path = os.path.join(path, components.pop(0))
        if os.path.isdir(path):
            continue
        os.mkdir(path)

def calc_shader_crc(shader_asm):
    # FUTURE: Use ctypes to call into d3dx.dll directly to remove need for
    # shaderasm.exe helper (may require native windows python - cygwin python
    # is missing some function calling conventions). Can always try both
    # methods.
    import subprocess, zlib
    helper = os.path.join(os.path.dirname(__file__), 'shaderasm.exe')

    # Once Python 3.4 gets into cygwin switch to this:
    # blob = subprocess.check_output([helper], input=shader_asm.encode('ascii'))

    p = subprocess.Popen([helper], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    (blob, _) = p.communicate(shader_asm.encode('ascii'))

    # I'm getting -11 (SEGV) in cygwin python for some reason, which I don't
    # see when running the command line - thinking it may be bogus.
    # if p.returncode != 0:
    #     print("shaderasm.exe helper failed with exit code %i" % p.returncode)
    #     raise subprocess.CalledProcessError()

    if not blob:
        return None

    return zlib.crc32(blob)

def add_shader_crc(sub_program):
    sub_program.crc = None
    if sub_program.name != 'd3d9':
        return
    try:
        sub_program.crc = calc_shader_crc(sub_program.shader_asm)
    except:
        pass
    if not sub_program.crc:
        print('WARNING: Unable to determine shader CRC32 - is shaderasm.exe installed?')

def add_header_crc(headers, sub_program):
    if sub_program.crc:
        headers[0] = 'CRC32: %.8X | %s' % (sub_program.crc, headers[0])

def index_headers(headers, sub_program):
    if sub_program.crc:
        crc_headers['%.8X' % sub_program.crc] = headers

def save_header_index():
    try:
        out = json.load(open(shader_idx_filename, 'r', encoding='utf-8'))
        out.update(crc_headers)
    except:
        out = crc_headers
    print('Saving header index %s...' % shader_idx_filename)
    json.dump(out, open(shader_idx_filename, 'w', encoding='utf-8'), sort_keys = True, indent = 0)

def add_vanity_tag(headers):
    if headers[-1] != '':
        headers.append('')
    headers.append("Headers extracted with DarkStarSword's extract_unity_shaders.py")
    headers.append("https://raw.githubusercontent.com/DarkStarSword/3d-fixes/master/extract_unity_shaders.py")

def _export_shader(sub_program, headers, path_components):
    mkdir_recursive(path_components[:-1])
    dest = os.path.join(os.curdir, *path_components)
    headers = commentify(headers)
    index_headers(headers, sub_program)
    print('Extracting %s.txt...' % dest)
    with open('%s.txt' % dest, 'w') as f:
        f.write(headers)
        f.write('\n\n')
        f.write(indent_like_helix(sub_program.shader_asm))

def export_shader(sub_program, args):
    headers = collect_headers(sub_program)
    add_header_crc(headers, sub_program)
    add_vanity_tag(headers)

    path_components = export_filename_combined([sub_program], args)
    if path_components is None:
        return
    return _export_shader(sub_program, headers, path_components)

def shader_name(tree):
    while tree.parent is not None:
        tree = tree.parent
    return tree.name

def dedupe_shaders(shader_list, args):
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
    add_header_crc(headers, shader_list[0])
    add_vanity_tag(headers)
    # print(commentify(headers))

    for shader in shaders:
        similar_shaders = filter(lambda x: shader_name(x) == shader, shader_list)
        path_components = export_filename_combined(similar_shaders, args)
        if path_components is None:
            return
        _export_shader(shader_list[0], headers, path_components)

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description = 'Unity Shader Extractor')
    parser.add_argument('shaders', nargs='+',
            help='List of compiled Unity shader files to parse')
    parser.add_argument('--filename-crc', '--name-crc', action='store_true',
            help='Name the files by the CRC of the shader, if possible')
    parser.add_argument('--flatten', action='store_true',
            help='Use alternate directory structure that only groups shaders by source shader and type (requires --filename-crc)')
    args = parser.parse_args()
    if args.flatten and not args.filename_crc:
        raise ValueError('--flatten must be used with --filename-crc or you risk filename conflicts!')
    return args

def main():
    global shader_list

    args = parse_args()
    processed = set()

    for filename in args.shaders:
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
            export_shader(shaders[0], args)
        else:
            # print('-'*79)
            dedupe_shaders(shaders, args)

    save_header_index()

if __name__ == '__main__':
    sys.exit(main())

# vi: sw=4:ts=4:expandtab
