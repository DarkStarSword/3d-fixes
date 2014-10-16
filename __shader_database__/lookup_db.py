#!/usr/bin/env python3

import sys, os
import json
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

def colourise_diff(diff):
    if not sys.stdout.isatty():
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

def print_shader_diff(orig_filename, shader):
    with open(orig_filename) as orig:
        fromlines = list(orig)
        tolines = shader.replace('\r\n', '\n').splitlines(True)
        diff = difflib.unified_diff(fromlines, tolines)
        sys.stdout.writelines(colourise_diff(diff))

def pretty_print_shader(filename, crc, shader):
    print('%s: %i distinct_fix fixes found' % (crc, len(shader)))
    for (i, distinct_fix) in enumerate(shader, 1):
        print('          %i.' % i)
        for post in distinct_fix['posts']:
            print('             "%s" - %s' % (post['title'], post['author']))
            print('               Post URL: %s' % post['url'])
            for download in post['downloads']:
                print('                 Download Link: %s' % download['url'])
                print('                      Location:   %s' % download['path'])
            print()
        # print(distinct_fix['shader'])
        print_shader_diff(filename, distinct_fix['shader'])
    print()

@shaderutil.handle_sigint
def main():
    global db_filename
    global download_dir

    if not os.path.isfile(db_filename):
        script_dir = os.path.join(os.curdir, os.path.dirname(sys.argv[0]))
        db_filename = os.path.join(script_dir, db_filename)
        download_dir = os.path.join(script_dir, download_dir)

    index = json.load(open(db_filename, 'r', encoding='utf-8'))

    filenames = sys.argv[1:]
    crcs = [shaderutil.get_filename_crc(filename) for filename in filenames]
    shaders_json = lookup_shaders_json(crcs, index)
    shaders = json.loads(shaders_json)
    for crc, shader in shaders.items():
        filename = filenames[crcs.index(crc)]
        pretty_print_shader(filename, crc, shader)

if __name__ == '__main__':
    sys.exit(main())

# vi: et sw=4 ts=4
