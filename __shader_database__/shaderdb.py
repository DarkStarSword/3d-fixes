#!/usr/bin/env/python

# Python 2 since Debian doesn't have a version of mod_python for apache that is
# compatible with Python3 yet and I would rather avoid manually installing it
# and inevitably never updating it.

from mod_python import apache
import os, re
import json
import zipfile
import rarfile # pip install rarfile

import shaderutil

script_dir = os.path.dirname(__file__)
db_filename = os.path.join(script_dir, 'SHADER_IDX.JSON')
download_dir = os.path.join(script_dir, 'downloads')

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

def lookup_shaders_json(crcs, index):
    result = {}
    for crc in crcs:
        r = lookup_shader_crc(crc, index)
        if r:
            result[crc] = r
    return json.dumps(result, sort_keys=True, indent=1)

is_crc_pattern = re.compile(r'^[0-9a-fA-F]{8}$')
def is_crc(crc):
	return is_crc_pattern.match(crc) is not None

def handle_get_crcs(req):
	req.content_type = 'application/json'
	crcs = set(map(str.strip, req.read().split()))
	if not all(map(is_crc, crcs)):
		return apache.HTTP_BAD_REQUEST

	index = json.load(open(os.path.join(script_dir, db_filename), 'r'))
	req.write(lookup_shaders_json(crcs, index))

	return apache.OK

handlers = {
	'get_crcs': handle_get_crcs,
}

def handler(req):
	req.content_type = 'application/json'
	filename = os.path.relpath(req.filename, script_dir)
	# req.write(filename)
	if filename in handlers:
		return handlers[filename](req)
	return apache.DECLINED


