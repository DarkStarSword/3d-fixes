#!/usr/bin/env python3

import sys, os
import re

def handle_sigint(f):
    def wrap(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except KeyboardInterrupt as e:
            print(e.__class__.__name__, file=sys.stderr)
    return wrap

shader_pattern = re.compile('''
  ^
  ((Vertex|Pixel)Shader_\d+_)?
  (CRC32_)?
  \s*
  (?P<CRC>[0-9a-f]{1,8})
  (_\d+)?
  (.txt)?
  $
''', re.VERBOSE | re.IGNORECASE)
def get_filename_crc(filename):
    basename = os.path.basename(filename)
    match = shader_pattern.match(basename)
    if match is None:
        raise Exception('Unable to determine CRC32 from filename - %s' % file)
    crc = match.group('CRC').upper()
    return '%s%s' % ('0'*(8-len(crc)), crc)

def url_to_download_path(url, download_dir):
    import urllib.parse
    parts = urllib.parse.urlparse(url)
    return os.path.join(download_dir, parts.netloc, parts.path.lstrip('/').replace('/', os.path.sep))

# vi: et sw=4 ts=4
