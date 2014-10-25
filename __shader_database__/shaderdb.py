#!/usr/bin/env/python3

import sys, os, re
import json
import zipfile
import rarfile # pip install rarfile

# ARE YOU SERIOUS WSGI?
sys.path.append(os.path.dirname(__file__))

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

def handle_get_crcs(environ, start_response):
	try:
		request_body_size = int(environ.get('CONTENT_LENGTH', 0))
	except ValueError:
		request_body_size = 0

	request = environ['wsgi.input'].read(request_body_size).decode('ascii')
	crcs = set(map(str.strip, request.split()))
	if not all(map(is_crc, crcs)):
		start_response('400 Bad Request', [])
		return []

	index = json.load(open(os.path.join(script_dir, db_filename), 'r'))
	ret = lookup_shaders_json(crcs, index).encode('utf-8')
	start_response('200 OK', [('Content-type', 'application/json'),
				('Content-Length', str(len(ret)))])
	return [ret]

handlers = {
	'/get_crcs': handle_get_crcs,
}

def application(environ, start_response):
	filename = environ['PATH_INFO']
	if filename in handlers:
		return handlers[filename](environ, start_response)

	start_response('404 Not Found', [])
	return []
