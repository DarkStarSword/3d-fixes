#!/usr/bin/env python3

# Similar idea to shadertool, but whereas there I implemented a full assembly
# parser and logic to analyse instruction streams, this is intended to use an
# approach based purely on pattern matching instead, which may not be as
# powerful, but should be simpler. This relies on matching the particular's of
# 3DMigoto's HLSL decompiler and I don't intend to turn this into a full HLSL
# parser - I'd be better off porting shadertool to DX11 since assembly language
# is easier to reason about programatically than HLSL.

import sys, os, re, collections, argparse, itertools, copy

import shadertool
from shadertool import debug, debug_verbose, component_set_to_string, vanity_comment, tool_name, expand_wildcards, game_git_dir

class Instruction(object):
    pattern = re.compile('[^;]*;')

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
        \s*
        =
        \s*
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

def InstructionFactory(text, pos):

    match = Comment.pattern.match(text, pos)
    if match is not None:
        return Comment(match.group()), match.end()

    match = AssignmentInstruction.pattern.match(text, pos)
    if match is not None:
        return AssignmentInstruction(match.group(), **match.groupdict()), match.end()

    match = Instruction.pattern.match(text, pos)
    if match is not None:
        return Instruction(match.group()), match.end()

    return None, pos


# Tried to get rid of all the edge cases, probably still some left...
vector_pattern = re.compile(r'''
    (?<![.])				(?# Prevent matching structs like foo.bar.baz)
    \b					(?# Ensure we start on a world boundary)
    (?P<variable>[a-zA-Z][a-zA-Z0-9]*)
    (?:[.](?P<components>[xyzw]+))?
    \b					(?# Ensure we end on a word boundary)
    (?![(.])				(?# Prevent matching float2\(...\) or not matching components)
''', re.VERBOSE)
Vector = collections.namedtuple('Vector', ['variable', 'components'])

def find_regs_in_expression(expression):
    '''
    Returns a list of scalar/vector variables used in an expression. Does
    not return structs or literals, intended to be used to find register
    accesses.
    '''
    pos = 0
    regs = []
    while True:
        match = vector_pattern.search(expression, pos)
        if match is None:
            break
        pos = match.end()
        vector = Vector(**match.groupdict())
        regs.append(vector)
    return regs

def expression_as_single_register(expression):
        match = vector_pattern.search(expression)
        if match is None:
            return None
        if expression[:match.start()].strip() or expression[match.end():].strip():
            return None
        return Vector(**match.groupdict())

def regs_overlap(vector, variable, components):
    if vector.variable != variable:
        return False

    if components is None:
        return True

    return set(components).intersection(set(vector.components))

def expression_is_register(expression, variable, components):
    if components is None and expression == variable:
        return True

    match = vector_pattern.match(expression)
    if match is None:
        return False

    vector = Vector(**match.groupdict())
    return regs_overlap(vector, variable, components)

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

class HLSLShader(object):
    main_start_pattern = re.compile(r'void main\(\s*')
    param_end_pattern = re.compile(r'\)\s*{')
    main_end_pattern = re.compile(r'^}$', re.MULTILINE)
    parameter_pattern = re.compile(r'''
        \s*
        (?P<output>out\s+)?
        (?P<type>(?:float|uint|int)[234]?)
        \s+
        (?P<variable>[a-zA-Z]\w*)
        \s*:\s*
        (?P<semantic>[a-zA-Z]\w*)
        \s*
        ,?
    ''', re.VERBOSE)
    Parameter = collections.namedtuple('Parameter', ['output', 'type', 'variable', 'semantic'])

    def __init__(self, filename):
        self.filename = filename
        self.autofixed = False
        self.vanity_inserted = False

        self.text = open(filename, 'r').read()

        self.main_match = self.main_start_pattern.search(self.text)
        self.param_end_match = self.param_end_pattern.search(self.text, self.main_match.end())
        main_end_match = self.main_end_pattern.search(self.text, self.param_end_match.end())

        self.declarations_txt = self.text[:self.main_match.start()]
        self.parameters_txt = self.text[self.main_match.end() : self.param_end_match.start()]
        body_txt = self.text[self.param_end_match.end() : main_end_match.start()]
        self.close_txt = self.text[main_end_match.start():main_end_match.end()]
        self.tail_txt = self.text[main_end_match.end():]

        self.parse_parameters()
        self.split_instructions(body_txt)

    def parse_parameters(self):
        self.parameters = {}
        pos = 0
        while True:
            match = self.parameter_pattern.match(self.parameters_txt, pos)
            if match is None:
                break
            pos = match.end()
            groups = match.groupdict()
            groups['output'] = groups['output'] and True or False
            param = self.Parameter(**groups)
            self.parameters[(param.semantic, param.output)] = param

    def split_instructions(self, body_txt):
        self.instructions = [];
        pos = 0
        while True:
            instr, pos = InstructionFactory(body_txt, pos)
            if instr is None:
                break

            if not instr.is_noop(): # No point adding noops, simplifies MGSV shaders
                self.instructions.append(instr)

            # Alternative noop handling - add line but comment it out:
            # if instr.is_noop(): # No point adding noops, simplifies MGSV shaders
            #     self.comment_out_instruction(-1, 'noop')

        self.close_txt = body_txt[pos:] + self.close_txt

    def lookup_semantic(self, semantic, output):
        return self.parameters[(semantic, output)]

    def lookup_output_position(self):
        try:
            return self.lookup_semantic('SV_Position0', True)
        except KeyError:
            return self.lookup_semantic('SV_POSITION0', True)

    def scan_shader(self, reg, components=None, write=None, start=None, end=None, direction=1, stop=False):
        '''
        Based on the same function in shadertool
        '''
        assert(direction == 1 or direction == -1)
        assert(write is not None)

        Match = collections.namedtuple('Match', ['line', 'instruction'])

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

        debug_verbose(1, "Scanning shader %s from instruction %i to %i for %s %s..." % (
            {1: 'downwards', -1: 'upwards'}[direction],
            start, end - direction,
            {True: 'write to', False: 'read from'}[write],
            str_reg_components(reg, components),
            ))

        if isinstance(components, str):
            components = set(components)

        ret = []
        for i in range(start, end, direction):
            instr = self.instructions[i]
            # debug('scanning %s' % instr.strip())
            if write:
                if instr.writes(reg, components):
                    debug_verbose(1, 'Found write on instruction %s: %s' % (i, instr.strip()))
                    ret.append(Match(i, instr))
                    if stop:
                        return ret
            else:
                if instr.reads(reg, components):
                    debug_verbose(1, 'Found read on instruction %s: %s' % (i, instr.strip()))
                    ret.append(Match(i, instr))
                    if stop:
                        return ret

        return ret

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
        comments = vanity_comment(args, self, what)
        for comment in comments:
            off += self.insert_instr(where + off, comment = comment)
        #self.declarations_txt = ''.join([ '// %s\n' % comment for comment in comments ]) + self.declarations_txt
        if not self.vanity_inserted:
            self.declarations_txt = '// %s\n' % comments[1] + self.declarations_txt
            self.vanity_inserted = True
        return off

    def insert_instr(self, pos, instruction=None, comment=None):
        line = '\n'
        if instruction is not None:
            line += instruction
        if instruction is not None and comment is not None:
            line += ' '
        if comment is not None:
            line += '// ' + comment
        self.instructions.insert(pos, line)
        return 1

    def __str__(self):
        s = self.declarations_txt
        s += self.main_match.group()
        s += self.parameters_txt
        s += self.param_end_match.group()
        for instr in self.instructions:
            s += str(instr)
        s += self.close_txt
        if not args.strip_tail:
            s += self.tail_txt
        return s

def auto_fix_vertex_halo(shader):
    '''
    Based on shadertool --auto-fix-vertex-halo
    '''

    # 1. Find output position variable from declarations
    pos_out = shader.lookup_output_position().variable

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
    if temp_reg.components and temp_reg.components != out_reg.components:
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
    #    temporary register:
    results = shader.scan_shader(temp_reg.variable, write=False, start=temp_reg_line + 1, end=output_line)
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
        shader.insert_instr(relocate_to, output_instr.strip(), 'Relocated to here with %s' % tool_name)
        output_line = relocate_to
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

    pos += shader.insert_instr(pos, 'float4 stereo = StereoParams.Load(0);')
    pos += shader.insert_instr(pos, '{0}.x += stereo.x * ({0}.w - stereo.y);'.format(temp_reg.variable))
    pos += shader.insert_instr(pos)

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

def install_shader(shader, file):
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

    parser.add_argument('--strip-tail', '-s', action='store_true',
            help='Strip everything after the main function in the shader')

    parser.add_argument('--auto-fix-vertex-halo', action='store_true',
            help="Attempt to automatically fix a vertex shader for common halo type issues")
    parser.add_argument('--only-autofixed', action='store_true',
            help="Installation type operations only act on shaders that were successfully autofixed with --auto-fix-vertex-halo")

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
    for file in args.files:
        debug_verbose(-2, 'parsing %s...' % file)
        shader = HLSLShader(file)

        if args.auto_fix_vertex_halo:
            auto_fix_vertex_halo(shader)

        real_file = file
        #if args.original:
        #    file = find_original_shader(file)

        if not args.only_autofixed or shader.autofixed:
            if args.output:
                print(shader, end='', file=args.output)
                #update_ini(shader)
            if args.in_place:
                tmp = '%s.new' % real_file
                print(shader, end='', file=open(tmp, 'w'))
                os.rename(tmp, real_file)
                #update_ini(shader)
            if args.install:
                if install_shader(shader, file):
                    #update_ini(shader)
                    pass
            if args.install_to:
                if install_shader_to(shader, file, args, os.path.expanduser(args.install_to), True):
                    #update_ini(shader)
                    pass
            if args.to_git:
                a = copy.copy(args)
                a.force = True
                if install_shader_to_git(shader, file, a):
                    #update_ini(shader)
                    pass

if __name__ == '__main__':
    main()

# vi: et ts=4:sw=4
