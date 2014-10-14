#!/usr/bin/env python3

import sys, os
import json

import shaderutil

def lookup_shader(filename, index):
    crc = shaderutil.get_filename_crc(filename)
    shaders = index['shaders']
    if crc not in shaders:
        return
    shader = shaders[crc]
    posts = index['posts']
    print('%s: %i distinct fixes found' % (crc, len(shader)))
    for i, sha in enumerate(shader, 1):
        print('          %i. %s' % (i, sha))
        for post_url in shader[sha]:
            post = posts[post_url]
            print('             "%s" - %s' % (post['title'], post['author']))
            print('               Post URL: %s' % post_url)
            for url in shader[sha][post_url]:
                print('                 Download Link: %s' % url)
    print()

@shaderutil.handle_sigint
def main():
    index = json.load(open('SHADER_IDX.JSON', 'r', encoding='utf-8'))
    for filename in sys.argv[1:]:
        lookup_shader(filename, index)

if __name__ == '__main__':
    sys.exit(main())

# vi: et sw=4 ts=4
