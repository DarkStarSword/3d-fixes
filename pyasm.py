#!/usr/bin/env python3

'''
Implements shader assembly like semantics in python

Provides a Register class which implements masks and swizzles, and a number of
functions which behave like the asm instructions.

The result is that shader assembly can be transformed to run in python without
too much massaging, increasing it's debuggability.

Note that the main difference when using this vs actual shader assembly is the
semantics of the destination register. Whereas in assembly you might do this:

mad r1, r2, r3, r4

Here you would move the destination register (r1) out like this:

r1 = mad(r2, r3, r4)

Make sure you use the mov() function to copy a register and not simply
assigning it, as the later would end up creating a reference, not a copy.
'''

class Register(object):
    # FUTURE: Might be better to make this type immutable so that something
    # like "r1 = r2; r2.x = 0" doesn't change r1.x (though this syntax should
    # not be used anyway: use r1 = mov(r2) and think like assembly)

    component_idx = {
        'x': 0, 'r': 0,
        'y': 1, 'g': 1,
        'z': 2, 'b': 2,
        'w': 3, 'a': 3,
    }

    def __init__(self, vals=None):
        if vals is None:
            vals = [0]*4
        else:
            try:
                if len(vals) != 4:
                    raise AttributeError(vals)
            except TypeError:
                vals = [vals]*4
        object.__setattr__(self, 'vals', vals)

    @classmethod
    def _validate_components(cls, components):
        if len(components) > 4:
            raise AttributeError(components)
        if set(components).difference(set(cls.component_idx)):
            raise AttributeError(components)

    def __getitem__(self, key):
        return self.vals[key]

    def __setitem__(self, key, value):
        self.vals[key] = value

    def __getattr__(self, components):
        # Read with swizzle
        self._validate_components(components)
        ret = Register()
        for i in range(4):
            try:
                component = self.component_idx[components[i]]
            except IndexError:
                # Short swizzle - reuse final component
                pass
            ret[i] = self.vals[component]
        return ret

    def __setattr__(self, components, value):
        # Write with mask
        self._validate_components(components)
        new_vals = self.vals[:]
        for component in 'xaybzcwd':
            if not components:
                break
            if component != components[0]:
                continue
            components = components[1:]
            component_idx = self.component_idx[component]
            try:
                val = value[component_idx]
            except TypeError:
                val = value
            new_vals[component_idx] = val;
        if components:
            raise AttributeError(components)
        object.__setattr__(self, 'vals', new_vals)

    def __neg__(self):
        return Register([ -x for x in self.vals ])

    def __len__(self):
        return 4

    def __repr__(self):
        return repr(self.vals)

def mov(source):
    return Register(source)

def add(source1, source2):
    return Register([ a + b for (a,b) in zip(source1, source2) ])

def mul(source1, source2):
    return Register([ a * b for (a,b) in zip(source1, source2) ])

def mad(source1, source2, source3):
    return Register([ a * b + c for (a,b,c) in zip(source1, source2, source3) ])

def dp3(source1, source2):
    return Register(sum(mul(source1.xyz, source2.xyz)[0:3]))

def dp4(source1, source2):
    return Register(sum(mul(source1.xyz, source2.xyz)))

def rcp(source):
    try:
        return Register(1 / source[0])
    except ZeroDivisionError:
        return Register(float('inf'))

def py_to_asm(function, **reg_replacements):
    '''
    Convert a python function implemented with pyasm registers and functions
    into shader assembly. Specify variable replacements with keyword arguments,
    e.g. py_to_asm(matrix._determinant_euclidean_asm_col_major,
                   col0='r20', col1='r21', col2='r22', det='r30', tmp0='r25')
    '''

    # I could have just used some regular expression search & replace and it
    # would have been much simpler, but I've been interested in learning about
    # Python's representation of itself for a while and this seemed like as
    # good an opportunity as any. This function is prety hacky and long as I
    # was figuring things out as I went. I might still go back to regexp...

    def delete_line(lineno):
        del source[lineno]
        del line_indents[lineno]
        del comments[lineno]
        ast.increment_lineno(tree, -1)

    def reg_name(target):
        # Return (register with swizzle/mask, register without swizzle/mask)
        prefix = ''
        if isinstance(target, ast.UnaryOp):
            assert(isinstance(target.op, ast.USub))
            prefix = '-'
            target = target.operand
        if isinstance(target, ast.Name):
            return ('{}{}'.format(prefix, target.id), target.id)
        if isinstance(target, ast.Attribute):
            reg = '{}{}.{}'.format(prefix, target.value.id, target.attr)
            return reg, target.value.id
        raise SyntaxError(target)

    def preprocess(source):
        # Syntax tree has whitespace & comments stripped, so use the tokenizer
        # to get them instead & strip out any pydoc.

        import tokenize, token, io

        line_indents = []
        comments = []

        def _preprocess(tokens):
            import token
            lineno = 0
            indent = comment = ''
            for t in tokens:
                if t.type == token.INDENT:
                    indent = t.string
                if t.type == tokenize.COMMENT:
                    comment = '//' + t.string[1:]
                if t.type in (token.NEWLINE, tokenize.NL):
                    line_indents.append(indent)
                    comments.append(comment)
                    # indent = '' - only counts new indents?
                    comment = ''
                    lineno += 1
                if t.type == token.STRING:
                    continue
                yield (t.type, t.string)

        stream = io.StringIO(source).readline
        stream = _preprocess(tokenize.generate_tokens(stream))
        source = tokenize.untokenize(stream)
        return source, line_indents, comments

    import ast, inspect
    source = inspect.getsource(function)
    source, line_indents, comments = preprocess(source)
    tree = ast.parse(source)

    # Transform python comments into assembly comments:
    source = source.replace('#', '//')

    # Split source into lines, and adjust ast line numbers to start at 0:
    source = source.splitlines()
    ast.increment_lineno(tree, -1)

    # Since we just got the source to the passed in function, there should be
    # exactly one function here:
    assert(len(tree.body) == 1)
    function = tree.body[0]
    delete_line(function.lineno)

    # Rename variables:
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            node.id = reg_replacements.get(node.id, node.id)
        if isinstance(node, ast.arg):
            node.arg = reg_replacements.get(node.arg, node.arg)

    # Get a list of inputs the function takes:
    inputs = [ a.arg for a in function.args.args ]
    registers = set(inputs[:])

    for statement in function.body:
        if isinstance(statement, ast.Return):
            # Since this will be pasted inline return is irrelevant:
            delete_line(statement.lineno)
            continue

        if isinstance(statement, ast.Assign):
            # Not expecting any code to use multiple destination targets:
            assert(len(statement.targets) == 1)
            target = statement.targets[0]
            reg, reg_bare = reg_name(target)

            instr = statement.value
            if isinstance(instr, ast.Attribute):
                assert(instr.value == 'pyasm')
                instr = instr.attr
            if instr.func.attr == 'Register':
                # TODO: If the register is initialised with constants we should
                # handle it specially
                delete_line(instr.lineno)
                continue

            registers.add(reg_bare)

            args = [reg] + [ reg_name(a)[0] for a in instr.args ]
            source[instr.lineno] = '{}{} {} {}'.format(
                    line_indents[instr.lineno],
                    instr.func.attr,
                    ', '.join(args),
                    comments[instr.lineno]).rstrip()

            continue

        raise SyntaxError(statement)

    print('\n'.join(source).strip('\n'))

    unbound = registers.difference(reg_replacements.values())
    if unbound:
        print('\n// UNBOUND REGISTERS:', ', '.join(sorted(unbound)))
