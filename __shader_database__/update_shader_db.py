#!/usr/bin/env python3

import json
from bs4 import BeautifulSoup
import urllib.request
import urllib.parse
import posixpath
import sys, os

blog_id = '5003459283230164005'
api_key = open('api-key.txt').read().strip()
url = 'https://www.googleapis.com/blogger/v3/blogs/%s/posts' % blog_id
fetch_all = True # TODO: Only fetch bodies for posts not already retrieved
ignorred_labels = set(['guide', 'hidden', 'misc'])

params = {
    'orderBy': 'updated',
    'fields': 'items(author/displayName,content,id,title,updated,url,labels),nextPageToken',
    'key': api_key,
    'maxResults': 1000000000, # Fucking page token only returned me 10+6 results! Is this really the only way to fetch everything?
    'fetchBodies': str(fetch_all).lower(),
}

def get_page(pageToken = None):
    p = params.copy()
    if pageToken is not None:
        p['pageToken'] = pageToken
    with urllib.request.urlopen('%s?%s' % (url, urllib.parse.urlencode(p))) as f:
        return json.loads(f.read().decode('utf-8')) # TODO: Read Content-Type header

def get_posts():
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

def download_file(dir, url):
    try:
        os.mkdir(dir)
    except OSError:
        pass
    parts = urllib.parse.urlparse(url)
    basename = posixpath.basename(parts.path)
    dest = os.path.join(dir, basename)
    if os.path.exists(dest):
        print('Skipping %s - already downloaded' % url)
        return # TODO: Check if file has changed or was only partially downloaded
    with open(dest, 'wb') as f:
        try:
            print('Downloading %s...' % url, end='')
            sys.stdout.flush()
            with urllib.request.urlopen(url) as download:
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

def handle_sigint(f):
    def wrap(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except KeyboardInterrupt as e:
            print(e.__class__.__name__, file=sys.stderr)
    return wrap

@handle_sigint
def main():
    if os.path.exists('POSTS.JSON'):
        print('WARNING: Loading existing POSTS.JSON instead of fetching from Blogger!')
        posts = json.load(open('POSTS.JSON', 'r', encoding='utf-8'))
    else:
        posts = get_posts()
        json.dump(posts, open('POSTS.JSON', 'w', encoding='utf-8'), sort_keys=True, indent=4)

    # enumerate_link_types(posts)
    links_done = set()
    for post in posts:
        if 'labels' in post:
            if set(post['labels']).intersection(ignorred_labels):
                continue
        found_link = False
        for link in filter_links(post['content']):
            found_link = True
            if link in links_done:
                continue
            try:
                download_file('downloads/%s-%s' % (post['id'], post['updated']), link)
            except Exception as e:
                print('%s occured while downloading %s: %s' % (e.__class__.__name__, link, str(e)))
            links_done.add(link)
        if not found_link:
            print('NO DOWNLOAD LINK? %s' % post['url'])

if __name__ == '__main__':
    sys.exit(main())

# vi: et sw=4 ts=4
