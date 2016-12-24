#!/usr/bin/env python3

import sys, re

pattern = re.compile('''\
  (?P<wpos>r[0-9])\.xyzw = (?P<FViewUniformShaderParameters>cb[0-9])\[37\]\.xyzw \* (?P<v>v[0-9])\.yyyy;
  (?P=wpos)\.xyzw = (?P=v)\.xxxx \* (?P=FViewUniformShaderParameters)\[36\]\.xyzw \+ (?P=wpos)\.xyzw;
  (?P=wpos)\.xyzw = (?P=v)\.zzzz \* (?P=FViewUniformShaderParameters)\[38\]\.xyzw \+ (?P=wpos)\.xyzw;
  (?P=wpos)\.xyzw = (?P=FViewUniformShaderParameters)\[39\]\.xyzw \+ (?P=wpos)\.xyzw;
  (?P=wpos)\.xyz = (?P=wpos)\.xyz / (?P=wpos)\.www;
''')

fix = '''\

// Common SVPositionToTranslatedWorld fix:
float4 s = StereoParams.Load(0);
matrix TranslatedWorldToClip = MATRIX({FViewUniformShaderParameters}, 0);
matrix ClipToTranslatedWorld = MATRIX({FViewUniformShaderParameters}, 32);
float4 t = mul({wpos}, TranslatedWorldToClip);
t.x -= s.x * (t.w - s.y);
{wpos} = mul(t, ClipToTranslatedWorld);

'''

main_pattern = re.compile('''\nvoid main\(''')
main_replace = '''#include "matrix.hlsl"\n\nvoid main('''
def include_matrix_hlsl(shader):
    return main_pattern.sub(main_replace, shader)

def fixup(file):
    shader = open(file, 'r').read()
    match = pattern.search(shader)
    if match is None:
        print('No match')
        return
    shader = shader[:match.end()] + fix.format(**match.groupdict()) + shader[match.end():]
    shader = include_matrix_hlsl(shader) # Do this last so as not to invalidate match.start()/end()
    print(shader)
    open(file, 'w').write(shader)

for arg in sys.argv[1:]:
    fixup(arg)
