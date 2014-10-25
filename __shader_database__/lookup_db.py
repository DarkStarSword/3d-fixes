#!/usr/bin/env python3

import sys, os
import json
import argparse
import difflib
import urllib.request
import urllib.parse

import shaderutil

api_url_base = 'http://valen.darkstarsword.net/apis/shaderdb/dev'
api_url_get_crcs = '%s/get_crcs' % api_url_base

def lookup_shader_crcs(crcs):
    data = '\n'.join(crcs).encode('ascii')
    try:
        print('Sending request to shader database server...', file=sys.stdout)
        with urllib.request.urlopen(api_url_get_crcs, data=data) as f:
            print('Retrieving result...', file=sys.stdout)
            ret = json.loads(f.read().decode('utf-8'))
            print('Done', file=sys.stdout)
            return ret
    except urllib.error.HTTPError as e:
        print(e.read().decode('utf-8'), file=sys.stderr)
        raise

def colourise_diff(diff, args):
    if not args.colour and not sys.stdout.isatty():
        for d in diff:
            yield d
    reset = '\x1b[0m'
    for d in diff:
        colour = None
        if d[0] == '+':
            yield '\x1b[32m%s%s' % (d, reset) # 32 = foreground green
        elif d[0] == '-':
            yield '\x1b[31m%s%s' % (d, reset) # 31 = foreground red
        else:
            yield d

def shader_diff(orig_filename, shader, zip_url):
    with open(orig_filename) as orig:
        fromlines = orig.read().replace('\r\n', '\n').replace('\0', '').splitlines(True)
        tolines = shader.replace('\r\n', '\n').replace('\0', '').splitlines(True)
        diff = difflib.unified_diff(fromlines, tolines, orig_filename, zip_url)
        for d in diff:
            yield d

def pretty_print_shader(filename, crc, shader, args):
    print('\n/' + '='*79)
    for (i, distinct_fix) in enumerate(shader, 1):
        print('|')
        print('>-+' + '-'*77)
        print('| | %s: Fix %i/%i' % (crc, i, len(shader)))
        zip_url = None
        for post in distinct_fix['posts']:
            print('| >-+' + '-'*75)
            print('| | | "%s" - %s' % (post['title'], post['author']))
            print('| | | Post URL: %s' % post['url'])
            print('| | \\-+' + '-'*73)
            for download in post['downloads']:
                print('| |   | Download: %s' % download['url'])
                print('| |   |           -> %s' % download['path'])
                if zip_url is None:
                    zip_url = '%s/%s' % (download['url'], download['path'])
            print('| |   \\' + '-'*73)
        if args.diff and os.path.isfile(filename):
            for diff in colourise_diff(shader_diff(filename, distinct_fix['shader'], zip_url), args):
                sys.stdout.write('| | %s' % diff)
        else:
            print(distinct_fix['shader'])
        print('| \\' + '-'*77)
    print('\\' + '='*79)

def parse_args():
    parser = argparse.ArgumentParser(description = 'Shader database lookup tool')
    parser.add_argument('files', nargs='+',
            help='List of shader assembly files or CRCs to look up')
    parser.add_argument('--colour', '--color', action='store_true',
            help='Force colour output, even if output is not attached to a tty')
    parser.add_argument('--no-diff', dest='diff', action='store_false',
            help='Disable diff output and suppress ascii lines around shaders')
    return parser.parse_args()

@shaderutil.handle_sigint
def main():
    args = parse_args()

    crcs = [shaderutil.get_filename_crc(filename) for filename in args.files]
    shaders = lookup_shader_crcs(crcs)
    for crc, shader in shaders.items():
        filename = args.files[crcs.index(crc)]
        pretty_print_shader(filename, crc, shader, args)

if __name__ == '__main__':
    sys.exit(main())

# vi: et sw=4 ts=4
