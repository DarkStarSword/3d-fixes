#!/usr/bin/env python3

import sys, os
import json
import argparse
import difflib
import zipfile
try:
    import rarfile
except ImportError:
    print('You need to run: pip3 install rarfile')
    raise

import shaderutil

db_filename = 'SHADER_IDX.JSON'
download_dir = 'downloads'

def extract_shader(archive, path):
    (_, ext) = os.path.splitext(archive)
    if ext == '.zip':
        Handler = zipfile.ZipFile
    elif ext == '.rar':
        Handler = rarfile.RarFile
    else:
        raise AssertionError('Unsupported archive format: %s' % ext)
    with Handler(archive) as archive:
        return archive.read(path).decode('utf-8')

def lookup_shader_crc(crc, index):
    shaders = index['shaders']
    if crc not in shaders:
        return []
    shader = shaders[crc]
    posts = index['posts']
    result = []
    for i, sha in enumerate(shader, 1):
        result_distinct = {
            'posts': [],
            'shader': None
        }
        for post_url in shader[sha]:
            post = posts[post_url]
            downloads = []
            for (url, zip_path) in shader[sha][post_url]:
                downloads.append({
                    'url': url,
                    'path': zip_path,
                })
                if result_distinct['shader'] is None:
                    filename = shaderutil.url_to_download_path(url, download_dir)
                    result_distinct['shader'] = extract_shader(filename, zip_path)
            result_distinct['posts'].append({
                    'title': post['title'],
                    'author': post['author'],
                    'url': post_url,
                    'downloads': downloads,
            })
        if result_distinct['shader'] is not None:
            result.append(result_distinct)
    return result

# This returns JSON because I want to stick it up on the web somewhere to allow
# clients to query it without needing a local copy of the database:
def lookup_shaders_json(crcs, index):
    result = {}
    for crc in crcs:
        r = lookup_shader_crc(crc, index)
        if r:
            result[crc] = r
    return json.dumps(result, sort_keys=True, indent=1)

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
        if os.path.isfile(filename):
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
    return parser.parse_args()

@shaderutil.handle_sigint
def main():
    global db_filename
    global download_dir

    args = parse_args()

    if not os.path.isfile(db_filename):
        script_dir = os.path.join(os.curdir, os.path.dirname(sys.argv[0]))
        db_filename = os.path.join(script_dir, db_filename)
        download_dir = os.path.join(script_dir, download_dir)

    index = json.load(open(db_filename, 'r', encoding='utf-8'))

    crcs = [shaderutil.get_filename_crc(filename) for filename in args.files]
    shaders_json = lookup_shaders_json(crcs, index)
    shaders = json.loads(shaders_json)
    for crc, shader in shaders.items():
        filename = args.files[crcs.index(crc)]
        pretty_print_shader(filename, crc, shader, args)

if __name__ == '__main__':
    sys.exit(main())

# vi: et sw=4 ts=4
