#!/usr/bin/env python3

import sys, re, os

pattern = re.compile('''\
  (?P<result>r[0-9]+.[xyzw]+) = HDRLighting__LensDirtTexture__TexObj__\.Sample\(HDRLighting__LensDirtTexture__SampObj___s, (?P<texcoords>r[0-9]+.[xyzw]+)\).xyz;
''')

fix = '''\

// Adjust lens grit:
{result} = HDRLighting__LensDirtTexture__TexObj__.Sample(HDRLighting__LensDirtTexture__SampObj___s, to_lens_grit_depth({texcoords})).xyz;

if (IniParams[7].z == -1)
    {result} = 0;

'''

main_pattern = re.compile('''\nvoid main\(''')
main_replace = '''#include "hud.hlsl"\n\nvoid main('''
def include_hud_hlsl(shader):
    return main_pattern.sub(main_replace, shader)

def fixup(file):
    shader = open(file, 'r').read()
    match = pattern.search(shader)
    if match is None:
        print('No match')
        return
    shader = shader[:match.start()] + fix.format(**match.groupdict()) + shader[match.end():]
    shader = include_hud_hlsl(shader) # Do this last so as not to invalidate match.start()/end()
    # print(shader)
    open(os.path.join('..', 'ShaderFixes', file), 'w').write(shader)

for arg in sys.argv[1:]:
    fixup(arg)
