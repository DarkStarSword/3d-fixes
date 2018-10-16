#!/usr/bin/env python3

import sys, os, re

set_shader = re.compile(r'''
    (?:(?P<frame>\d+)\.)?
    (?P<call>\d+)
    \s+
    (?P<type>[VHDGPC]S)
    SetShader\(.*\)
    \s+
    hash=(?P<hash>[0-9a-fA-F]{16})
''', re.VERBOSE)

#TODO: OMSetRenderTargetsAndUnorderedAccessViews NumRTVs != -1
set_rtvs = re.compile(r'''
    (?:(?P<frame>\d+)\.)?
    (?P<call>\d+)
    \s+
    OMSetRenderTargets\(.*\)
    \s*
''', re.VERBOSE)

set_rtv_details = re.compile(r'''
    \s+
    (?P<slot>[0-7D]):
    \s+
    view=(?P<view>0x[0-9a-fA-F]{16})
    \s+
    resource=(?P<resource>0x[0-9a-fA-F]{16})
    (?:
        \s*
        hash=(?P<hash>[0-9a-fA-F]{8})
    )?
''', re.VERBOSE)

draw = re.compile(r'''
    (?:(?P<frame>\d+)\.)?
    (?P<call>\d+)
    \s+
    Draw\S*\(.*\)
    \s*
''', re.VERBOSE)

dispatch = re.compile(r'''
    (?:(?P<frame>\d+)\.)?
    (?P<call>\d+)
    \s+
    Dispatch\S*\(.*\)
    \s*
''', re.VERBOSE)

def main():
    for file in sys.argv[1:]:
        current_shaders = {
            'VS': 0x0000000000000000,
            'HS': 0x0000000000000000,
            'DS': 0x0000000000000000,
            'GS': 0x0000000000000000,
            'PS': 0x0000000000000000,
            'CS': 0x0000000000000000,
        }
        shaders = {}
        current_rtvs = [0] * 9
        matching_rtvs = False
        rtvs = 0

        for line in open(file, 'r').readlines():
            if matching_rtvs:
                match = set_rtv_details.match(line)
                if match:
                    slot = match.group('slot')
                    if slot == 'D':
                        current_rtvs[8] = match.group('resource')
                    else:
                        current_rtvs[int(slot)] = match.group('resource')
                    continue
                else:
                    matching_rtvs = False

            match = set_rtvs.match(line)
            if match:
                current_rtvs = [0] * 9
                matching_rtvs = True
                continue

            match = set_shader.match(line)
            if match:
                current_shaders[match.group('type')] = int(match.group('hash'), 16)
                continue

            match = draw.match(line)
            if match:
                types = ('VS', 'HS', 'DS', 'GS', 'PS')
                num_current_rtvs = len(list(filter(None, current_rtvs))) # FIXME: + number of UAVs bound to PS
            else:
                match = dispatch.match(line)
                if not match:
                    continue
                types = ('CS',)
                num_current_rtvs = 1 # FIXME: Number of UAVs bound to CS

            rtvs += num_current_rtvs
            call = int(match.group('call'))
            for type in types:
                hash = current_shaders[type]
                if not hash:
                    continue
                shaders.setdefault((type, hash), [])
                shaders[(type, hash)].append((call, rtvs, num_current_rtvs))

        total_calls = call
        total_rtvs = rtvs
        call = 0
        print('                    draw  render  total   num')
        print('                   calls  targets shader  rtvs')
        print('                   saved  saved    uses  (first)')
        for shader in sorted(shaders, key = lambda x: shaders[x][0]):
            #if len(shaders[shader]) > 1:
            #    continue
            if shaders[shader][0][0] == call:
                continue
            call = shaders[shader][0][0]
            print('%s %016x %3i%%  %3i%%      %-7i %i' % (shader[0], shader[1],
                shaders[shader][0][0] / total_calls * 100,
                shaders[shader][0][1] / total_rtvs * 100,
                len(shaders[shader]),
                shaders[shader][0][2]))

if __name__ == '__main__':
    main()

# vi: et ts=4:sw=4
