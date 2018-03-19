#!/usr/bin/env python3

import argparse, textwrap, sys
from PIL import Image, ImageFont, ImageDraw

class FontTooLarge(Exception): pass

# Also hardcoded in the font shader, so you would need to edit that as well to
# change these:
chars_across = 16
chars_down = 6

def render_font(font, size):
    char_width = args.char_width
    char_height = args.char_height
    image = Image.new('L', (char_width * chars_across, char_height * chars_down))
    pixels = image.load()
    colour = 255

    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font, size)
    # font = ImageFont.load_default()

    for c in range(0x20, 0x7f):
        w, h = font.getsize(chr(c))
        print('"%c": %ix%i' % (chr(c), w, h), end=', ')
        if w > char_width or h > char_height:
            raise FontTooLarge()
        x = c % chars_across
        y = (c // chars_across - 2)
        draw.text((x * char_width, y * char_height), chr(c), font=font, fill=colour)
        # Encode the dimensions in the pixels of character 127:
        pixels[(chars_across-1) * char_width + x, (chars_down-1) * char_height + y*2    ] = w
        pixels[(chars_across-1) * char_width + x, (chars_down-1) * char_height + y*2 + 1] = h

    return image

def parse_args():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument('font')
    parser.add_argument('output')
    parser.add_argument('--font-size', type=int, default=24)
    parser.add_argument('--char-size', type=int)
    parser.add_argument('--char-width', type=int, default=16)
    parser.add_argument('--char-height', type=int, default=16)
    args = parser.parse_args()

    if args.char_size is not None:
        args.char_width = args.char_size
        args.char_height = args.char_size

    if args.char_width < chars_across:
        parser.error('Character width must be at least %i' % chars_across)
    if args.char_height < chars_down * 2:
        parser.error('Character height must be at least %i' % (chars_down * 2))

def main():
    parse_args()

    size = args.font_size
    while size:
        try:
            print('Trying font size %i...' % size)
            image = render_font(args.font, size)
        except FontTooLarge:
            print('Character too large')
            size -= 1
            if size == 0:
                raise
        except OSError:
            print('Cannot open "%s". Try using the full pathname to the font.' % args.font)
            sys.exit(1)
        else:
            break
    print('\n\nSaving font to %s' % args.output)
    image.save(args.output)

if __name__ == '__main__':
    main()
