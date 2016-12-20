#!/usr/bin/env python

import argparse, textwrap
from PIL import Image, ImageFont, ImageDraw

def render_font(font, size):
    char_width = 16
    char_height = 16
    image = Image.new('L', (char_width * 16, char_height * 6))
    pixels = image.load()
    colour = 255

    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font, size)
    # font = ImageFont.load_default()

    for c in range(0x20, 0x7f):
        w, h = font.getsize(chr(c))
        print(chr(c), w, h)
        if w > char_width or h > char_height:
            raise Exception('Font too large')
        x = c % 16
        y = (c // 16 - 2)
        draw.text((x * char_width, y * char_height), chr(c), font=font, fill=colour)
        # Encode the dimensions in the pixels of character 127:
        pixels[15 * char_width + x, 5 * char_height + y*2    ] = w
        pixels[15 * char_width + x, 5 * char_height + y*2 + 1] = h

    return image

def parse_args():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument('font')
    parser.add_argument('output')
    args = parser.parse_args()

def main():
    parse_args()

    size = 24
    while size:
        try:
            print('Trying size', size)
            image = render_font(args.font, size)
        except:
            size -= 1
            if size == 0:
                raise
        else:
            break
    image.save(args.output)

if __name__ == '__main__':
    main()
