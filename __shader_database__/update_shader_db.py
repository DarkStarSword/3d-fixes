#!/usr/bin/env python3

import sys, os
if not (sys.version_info.major > 3 or (sys.version_info.major == 3 and sys.version_info.minor >= 3)):
    # urllib.request.Request doesn't support method
    # Alternatively, we could use the old http module instead
    raise Exception('Please upgrade Python to 3.3 or higher')

import json
from bs4 import BeautifulSoup
import urllib.request
import urllib.parse
import posixpath
import time
import re
import hashlib
import zipfile
try:
    import rarfile
except ImportError:
    print('You need to run: pip install rarfile')
    raise

import http_date
import shaderutil

blog_id = '5003459283230164005'
api_key = None
api_url = 'https://www.googleapis.com/blogger/v3/blogs/%s' % blog_id
fetch_all = True # TODO: Only fetch bodies for posts not already retrieved
ignorred_labels = set(['guide', 'hidden', 'misc'])
download_dir = 'downloads'
shader_pattern = re.compile('^[0-9A-F]{8}.txt$', re.IGNORECASE)
poll_updates = 14 * 24 * 60 * 60 # atime of a downloaded file must be at least this old to check for updates

def query_blogger_api(url, params):
    url = '%s?%s' % (url, urllib.parse.urlencode(params))
    # print('fetching %s' % url)
    with urllib.request.urlopen(url) as f:
        return json.loads(f.read().decode('utf-8')) # TODO: Read Content-Type header

def get_blog_updated():
    params = {
        'fields': 'updated',
        'key': api_key,
    }
    return query_blogger_api(api_url, params)['updated']

def get_page(pageToken = None):
    params = {
        'orderBy': 'updated',
        'fields': 'items(author/displayName,content,id,title,updated,url,labels),nextPageToken',
        'key': api_key,
        'maxResults': 500, # Fucking page token only returned me 10+6 results! Is this really the only way to fetch everything?
        'fetchBodies': str(fetch_all).lower(),
    }
    if pageToken is not None:
        params['pageToken'] = pageToken
    return query_blogger_api('%s/posts' % api_url, params)

def get_blog_posts():
    pageToken = None
    posts = []
    for i in range(3):
        j = get_page(pageToken)
        print('Fetched page %i (%i posts)...' % (i, len(j['items'])))
        # print(json.dumps(j, sort_keys=True, indent=4))
        posts.extend(j['items'])
        if 'nextPageToken' not in j:
            break
        pageToken = j['nextPageToken']
    return posts

def find_links(content):
    soup = BeautifulSoup(content)
    for link in soup.find_all('a'):
        yield link.get('href')

def enumerate_link_types(posts):
    schemes = set()
    extensions = set()
    for post in posts:
        for link in find_links(post['content']):
            parts = urllib.parse.urlparse(link)
            if parts.scheme:
                schemes.add(parts.scheme)
            if parts.path:
                basename = posixpath.basename(parts.path)
                (root, ext) = posixpath.splitext(basename)
                if ext:
                    extensions.add(ext)
    print('Schemes:')
    print('\n'.join(schemes))
    print()
    print('Extensions:')
    print('\n'.join(extensions))

def filter_links(content):
    for link in find_links(content):
        # print(link)
        parts = urllib.parse.urlparse(link)
        if parts.scheme not in ('http', 'https', 'ftp'):
            continue
        if not parts.path:
            continue
        basename = posixpath.basename(parts.path)
        (root, ext) = posixpath.splitext(basename)
        if not ext or ext.lower() not in ('.zip', '.rar'):
            continue
        yield link

def recursive_mkdir(path):
    tree, leaf = os.path.split(path)
    if tree:
        recursive_mkdir(tree)
    try:
        os.mkdir(path)
    except OSError as e:
        pass

def get_url_last_modified(url):
    req = urllib.request.Request(url, method='HEAD')
    with urllib.request.urlopen(req) as f:
        return http_date.parse_http_date(f.getheader('Last-Modified'))

def download_file(url):
    try:
        os.mkdir(download_dir)
    except OSError:
        pass
    dest = shaderutil.url_to_download_path(url, download_dir)

    if os.path.exists(dest):
        st = os.stat(dest)
        if time.time() - st.st_atime < poll_updates:
            # FIXME: atime may not be the best thing to use since it can be
            # updated by other things and then we may never check for updates
            return dest
        last_modified = get_url_last_modified(url)
        if int(st.st_mtime) == last_modified:
            # FIXME: Also check file size matches Content-Length
            # print('Skipping %s - up to date' % url)
            return dest
        rename_to = '%s~%s' % (time.strftime("%Y%m%d%H%M%S", time.gmtime(st.st_mtime)), os.path.basename(dest))
        rename_to = os.path.join(os.path.dirname(dest), rename_to)
        print('%s updated' % url)
        os.rename(dest, rename_to)
        print('old file backed up as %s' % rename_to)
    recursive_mkdir(os.path.dirname(dest))
    with open(dest, 'wb') as f:
        try:
            print('Downloading %s...' % url, end='')
            sys.stdout.flush()
            with urllib.request.urlopen(url) as download:
                last_modified = http_date.parse_http_date(download.getheader('Last-Modified'))
                while True:
                    buf = download.read(64*1024)
                    if not buf:
                        break
                    f.write(buf)
                    print('.', end='')
                    sys.stdout.flush()
                print('Done.')
        except:
            try:
                os.remove(dest)
            except:
                pass
            else:
                print('\nRemoved partially downloaded %s' % dest)
            raise
    os.utime(dest, (time.time(), last_modified))
    return dest

def list_shaders(filename):
    (_, ext) = os.path.splitext(filename)
    if ext == '.zip':
        Handler = zipfile.ZipFile
    elif ext == '.rar':
        Handler = rarfile.RarFile
    else:
        raise AssertionError('Unsupported archive format: %s' % ext)
    with Handler(filename) as archive:
        for zip_path in archive.namelist():
            basename = os.path.basename(zip_path)
            if shader_pattern.match(basename):
                (crc, ext) = os.path.splitext(basename)
                shader = archive.read(zip_path)
                sha = hashlib.sha1(shader).hexdigest()
                yield(crc.upper(), sha, zip_path)

shader_index = {}
post_index = {}
def index_shaders(post, filename, link):
    url = post['url']
    for (crc, sha, zip_path) in list_shaders(filename):
        if crc not in shader_index:
            shader_index[crc] = {}
        if sha not in shader_index[crc]:
            shader_index[crc][sha] = {}
        if url not in shader_index[crc][sha]:
            shader_index[crc][sha][url] = set()
        shader_index[crc][sha][url].add((link, zip_path))
        post_index[post['url']] = {
                'title': post['title'],
                'author': post['author']['displayName'],
        }

def process_link(post, link):
    try:
        filename = download_file(link)
    except Exception as e:
        print('%s occured while downloading %s: %s' % (e.__class__.__name__, link, str(e)))
    else:
        index_shaders(post, filename, link)

class JSONSetEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, set):
            return list(o)
        return json.JSONEncoder.default(self, o)

def save_shader_index():
    print('Saving SHADER_IDX.JSON...')
    encoder = JSONSetEncoder(sort_keys=True, indent=1)
    data = {
        'shaders': shader_index,
        'posts': post_index,
    }
    with open('SHADER_IDX.JSON.NEW', 'w', encoding='utf-8') as f:
        for chunk in encoder.iterencode(data):
            f.write(chunk)
    os.rename('SHADER_IDX.JSON.NEW', 'SHADER_IDX.JSON')

def get_posts():
    updated = get_blog_updated()
    if os.path.exists('POSTS.JSON'):
        j = json.load(open('POSTS.JSON', 'r', encoding='utf-8'))
        if updated == j['updated']:
            print('Blog updated timestamp unchanged - using cached POSTS.JSON')
            return j['posts']
    print('Fetching blog posts...')
    posts = get_blog_posts()
    j = {'updated': updated, 'posts': posts}
    json.dump(j, open('POSTS.JSON', 'w', encoding='utf-8'), sort_keys=True, indent=4)
    return posts

def get_api_key():
    global api_key
    api_key = open('api-key.txt').read().strip()

@shaderutil.handle_sigint
def main():
    # Change the working to where the script is so we always use the same
    # database no matter where we are run from.
    os.chdir(os.path.dirname(__file__))

    get_api_key()
    posts = get_posts()

    # enumerate_link_types(posts)
    for post in posts:
        if 'labels' in post:
            if set(post['labels']).intersection(ignorred_labels):
                continue
        found_link = False
        links_done = set()
        for link in filter_links(post['content']):
            found_link = True
            if link in links_done:
                continue
            process_link(post, link)
            links_done.add(link)
        if not found_link:
            print('NO DOWNLOAD LINK? %s' % post['url'])

    if os.path.exists('MANUAL_POSTS.JSON'):
        posts = json.load(open('MANUAL_POSTS.JSON', 'r', encoding='utf-8'))
        for post in posts:
            for link in post['links']:
                process_link(post, link)

    save_shader_index()

if __name__ == '__main__':
    sys.exit(main())

# vi: et sw=4 ts=4
