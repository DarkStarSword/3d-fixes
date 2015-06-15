#!/usr/bin/env python3

from PIL import Image
import sys, os

# This is not optimised - there are much faster ways to do this, but it was
# faster for me to code it this way then to figure out which functions do what
# in PIL, and I only need this occasionally so whatever.

def deinterlace(image):
    f1 = Image.new(image.mode, (image.size[0], image.size[1] // 2))
    f2 = Image.new(image.mode, (image.size[0], image.size[1] // 2))
    p = image.load()
    p1 = f1.load()
    p2 = f2.load()
    for y in range(image.size[1] // 2):
        for x in range(image.size[0]):
            p1[x, y] = p[x, y * 2]
            p2[x, y] = p[x, y * 2 + 1]
    return (f1, f2)

def double_height(image):
    return image.resize((image.size[0], image.size[1] * 2), Image.BILINEAR)

def side_by_side(left, right):
    assert(left.mode == right.mode)
    assert(left.size == right.size)
    w, h = left.size
    image = Image.new(left.mode, (w * 2, h))
    p = image.load()
    pl = left.load()
    pr = right.load()
    for y in range(h):
        for x in range(w):
            p[x, y] = pl[x, y]
            p[w + x, y] = pr[x, y]
    return image

def main():
    for file in sys.argv[1:]:
        image = Image.open(file)
        (left, right) = map(double_height, deinterlace(image))
        image = side_by_side(left, right)
        new_filename = os.path.splitext(file)[0] + '.jps'
        image.save(new_filename, 'jpeg')

if __name__ == '__main__':
    main()
