#!/usr/bin/env python3

# Port of shadertool to DX11. I thought long and hard about adapting shadertool
# to work with both, but eventually decided to make a clean start since there
# are quite a few differences between DX9 and DX11 shaders, and this way I
# could take a clean slate with some of the lessons learned working on
# shadertool and hlsltool and have cleaner code from the beginning. Some code
# from shadertool and hlsltool is still reused. Like hlsltool this is intended
# to use an approach based purely on pattern matching instead of the parser in
# shadertool, which may not be as powerful, but should be simpler.

import sys, os, re, collections, argparse, itertools, copy

import shadertool, hlsltool

from shadertool import debug, debug_verbose, component_set_to_string
from shadertool import vanity_comment, tool_name, expand_wildcards
from shadertool import game_git_dir, collected_errors, show_collected_errors

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
        \s*
        ,
        \s*
        (?P<rval>\S.*)
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE)

    def __init__(self, text, instruction, lval, rval):
        hlsltool.AssignmentInstruction.__init__(self, text, lval, rval)
        self.instruction = instruction

    def is_noop(self):
        return False

class ResourceLoadInstruction(AssignmentInstruction):
    pattern = re.compile(r'''
        \s*
        (?P<instruction>[a-zA-Z_]+)
            \s*
            \(
                [^)]+
            \)
            \(
                [^)]+
            \)
        \s*
        (?P<lval>\S+)
        \s*
        ,
        \s*
        (?P<rval>\S.*)
        \s*
        $
    ''', re.MULTILINE | re.VERBOSE)

class Declaration(Instruction):
    pattern = re.compile(r'''
        \s*
        dcl_.*
        $
    ''', re.MULTILINE | re.VERBOSE)

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
    TempsDeclaration,
    SVOutputDeclaration,
    Declaration,
    ReturnInstruction,
    ResourceLoadInstruction,
    AssignmentInstruction,
)

class ASMShader(hlsltool.Shader):
    shader_model_pattern = re.compile(r'^[vhdgpc]s_[45]_[01]$', re.MULTILINE)

    def __init__(self, filename):
        hlsltool.Shader.__init__(self, filename)

        self.temps = None
        self.early_insert_pos = 0

        self.shader_model_match = self.shader_model_pattern.search(self.text)
        self.shader_model = self.shader_model_match.group()

        self.header_txt = self.text[:self.shader_model_match.start()]
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

    def lookup_output_position(self):
        return self.sv_outputs['position'].register.variable

    def effective_swizzle(self, mask, swizzle):
        if mask and not swizzle:
            return mask
        swizzle4 = swizzle + swizzle[-1] * (4-len(swizzle))
        if not mask:
            return swizzle4
        ret = ''
        for component in mask:
            ret += {
                'x': swizzle4[0],
                'y': swizzle4[1],
                'z': swizzle4[2],
                'w': swizzle4[3],
            }[component]
        return ret

    def insert_vanity_comment(self, where, what):
        off = 0
        off += self.insert_instr(where + off)
        comments = vanity_comment(args, self, what)
        for comment in comments:
            off += self.insert_instr(where + off, comment = comment)
        self.vanity_inserted = True
        return off

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
            self.declarations.append(Declaration('\n' + declaration))
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

    def insert_halo_fix_code(self, pos, temp_reg):
        off = 0
        off += self.insert_instr(pos + off, 'ne {0}.w, {1}.w, l(1.0)'.format(self.stereo_params_reg, temp_reg.variable))
        off += self.insert_instr(pos + off, 'if_nz {0}.w'.format(self.stereo_params_reg))
        off += self.insert_instr(pos + off, '  add {0}.w, {1}.w, -{0}.y'.format(self.stereo_params_reg, temp_reg.variable))
        off += self.insert_instr(pos + off, '  mad {1}.x, {0}.w, {0}.x, {1}.x'.format(self.stereo_params_reg, temp_reg.variable))
        off += self.insert_instr(pos + off, 'endif')
        return off

    def __str__(self):
        s = self.header_txt
        s += self.shader_model_match.group()
        for instr in self.declarations:
            s += str(instr)
        for instr in self.instructions:
            s += str(instr)
        return s

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
    for file in args.files:
        debug_verbose(-2, 'parsing %s...' % file)
        shader = ASMShader(file)

        try:
            if args.auto_fix_vertex_halo:
                hlsltool.auto_fix_vertex_halo(shader)
            pass
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
            if args.in_place:
                tmp = '%s.new' % real_file
                print(shader, end='', file=open(tmp, 'w'))
                os.rename(tmp, real_file)
                shader.update_ini()
            if args.install:
                if hlsltool.install_shader(shader, file, args):
                    shader.update_ini()
                    pass
            if args.install_to:
                if hlsltool.install_shader_to(shader, file, args, os.path.expanduser(args.install_to), True):
                    shader.update_ini()
                    pass
            if args.to_git:
                a = copy.copy(args)
                a.force = True
                if hlsltool.install_shader_to_git(shader, file, a):
                    shader.update_ini()
    show_collected_errors()
    hlsltool.do_ini_updates()

if __name__ == '__main__':
    main()

# vi: et ts=4:sw=4
