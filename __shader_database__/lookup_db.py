#!/usr/bin/env python3

import sys, os
import json
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

# This returns JSON because I want to stick it up on the web somewhere to allow
# clients to query it without needing a local copy of the database:
def lookup_shader_json(crc, index):
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

# TODO: Return result in JSON and stick it on a web API
def lookup_shader(filename, index):
    crc = shaderutil.get_filename_crc(filename)
    print('%s: %s' % (filename, json.dumps(lookup_shader_json(crc, index), sort_keys=True, indent=2)))
    # shaders = index['shaders']
    # if crc not in shaders:
    #     return
    # shader = shaders[crc]
    # posts = index['posts']
    # print('%s: %i distinct fixes found' % (crc, len(shader)))
    # for i, sha in enumerate(shader, 1):
    #     print('          %i.' % i)
    #     for post_url in shader[sha]:
    #         post = posts[post_url]
    #         print('             "%s" - %s' % (post['title'], post['author']))
    #         print('               Post URL: %s' % post_url)
    #         for (url, zip_path) in shader[sha][post_url]:
    #             print('                 Download Link: %s' % url)
    #             print('                      Location:   %s' % zip_path)
    #         print()
    # print()

@shaderutil.handle_sigint
def main():
    global db_filename
    global download_dir

    if not os.path.isfile(db_filename):
        script_dir = os.path.join(os.curdir, os.path.dirname(sys.argv[0]))
        db_filename = os.path.join(script_dir, db_filename)
        download_dir = os.path.join(script_dir, download_dir)

    index = json.load(open(db_filename, 'r', encoding='utf-8'))
    for filename in sys.argv[1:]:
        lookup_shader(filename, index)

if __name__ == '__main__':
    sys.exit(main())

# vi: et sw=4 ts=4
