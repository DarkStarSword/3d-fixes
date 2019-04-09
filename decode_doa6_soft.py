#!/usr/bin/env python3

import os, struct, sys, numpy, io, copy
numpy.set_printoptions(suppress = True,
        formatter = {
            #'int': lambda x : '%08x' % x,
            'float': lambda x: '%.2f' % x
        },
        edgeitems = numpy.inf)

region_unk_header = numpy.dtype([
    ('u10', numpy.float32, 8),
    ('u11', numpy.float32, 3),
    ('u12', numpy.float32, 3),
    ('u13', numpy.uint32, 1),
    ('u14', numpy.float32, 1),
    ('u15', numpy.float32, 2),
    ('u16', numpy.float32, 6),
])

node_fmt = numpy.dtype([
    ('id', numpy.uint32, 1),
    ('pos', numpy.float32, 3),
    ('rot', numpy.float32, 3), # Maybe
    ('0x43', numpy.uint32, 1),
    ('b', numpy.uint8, 4),
    ('links', numpy.uint32, 1),
])

def decode_node(f):
    buf = f.read(10*4)
    node, = numpy.frombuffer(buf, node_fmt)
    print('Node', node['id'], node)
    #assert(node['0x43'] == 0x43)

    # Other nodes this one influences and/or is influenced by:
    for i in range(node['links'] + 1):
        data = struct.unpack('<If', f.read(2*4))
        print('  Link %i: %.2f' % data)

    data = struct.unpack('<3f3I', f.read(6*4))
    #assert(data == (0,)*6)
    assert(data[3:] == (0,)*3)
    if data != (0,)*6:
        print(' ', data[:3])


def decode_soft_node_region(f):
    header = struct.unpack('<13I', f.read(13*4))
    (u1, len1, z2, z3, u4, len2, len3, u5, u6, u7, z8, o9, len4) = header
    print('Soft region header', header)

    # Assertions to catch any variants we haven't seen before:
    #assert(header == (0, 217, 0, 0, 9, 217, 58, 100, 1, 3, 0, 1, 217)) # len: 21836, pt2 len: 401*4 (217 + 9 + 1 + 3*58 ?), pt3 len: 494*4
    #assert(header == (1, 217, 0, 0, 9, 217, 58, 101, 1, 3, 0, 1, 217)) # len: 21836, pt2 len: 401*4 (217 + 9 + 1 + 3*58 ?), pt3 len: 494*4
    #assert(header == (4, 104, 0, 0, 9, 104, 58, 102, 0, 1, 0, 1, 104)) # len: 12900, pt2 len: 287*4 (104 + 9 + 0 + 3*58 ?), pt3 len: 268*4
    #assert(header == (5, 104, 0, 0, 9, 104, 70, 103, 0, 1, 0, 1, 104)) # len: 13044, pt2 len: 323*4 (104 + 9 + 0 + 3*70 ?), pt3 len: 268*4
    assert(u1 in (0,1,4,5)) # ID?
    assert(z2 == 0)
    assert(z3 == 0)
    assert(u4 == 9)
    assert(u5 in (100, 101, 102, 103)) # ID?
    assert(u6 in (0, 1))
    assert(u7 in (1, 3))
    assert(z8 == 0)
    assert(o9 == 1)
    assert(len1 == len2 == len4)

    # Probably just part of the same header. Might define the bounding box and
    # so on, though doesn't quite look right compared to what I believe are the
    # node positions, so unsure. Splitting this from the above read mostly to
    # use the numpy formatter.
    buf = f.read(24*4)
    unknown, = numpy.frombuffer(buf, region_unk_header)
    print('Soft region unknown', unknown)

    for i in range(len1):
        decode_node(f)

    # Next follows several lists of node IDs. The length of each list seems to
    # be from various fields in the header, but the contents of the individual
    # lists doesn't matter so much to us so I haven't confirmed that the lists
    # are actually in this order so they might be mixed up (but looks right):
    print(numpy.frombuffer(f.read(u4   * 4), numpy.uint32))
    print(numpy.frombuffer(f.read(len1 * 4), numpy.uint32))
    print(numpy.frombuffer(f.read(u6   * 4), numpy.uint32))
    print(numpy.frombuffer(f.read(len3 * 4 * 3), numpy.dtype([('node', numpy.uint32, 3)])))

    # Next follows a list of floats. Conveniently it gives us the section
    # length in bytes that we can skip over:
    (_6, len5) = struct.unpack('<2I', f.read(8))
    assert(_6 == 6)
    print(numpy.frombuffer(f.read(len5 - 8), numpy.float32))

def decode_soft_node_regions(f):
    num_regions, = struct.unpack('<I', f.read(4))
    for i in range(num_regions):
        decode_soft_node_region(f)
        print()

    assert(not f.read())

def print_unknown(name, buf):
    orig_opts = numpy.get_printoptions()
    opts = copy.deepcopy(orig_opts)
    opts['formatter']['int'] = lambda x : '%08x' % x
    numpy.set_printoptions(**opts)

    print(name)
    print(numpy.frombuffer(buf, numpy.uint32))

    numpy.set_printoptions(**orig_opts)

def dump_unknown_section(f):
    print_unknown('Unknown section:', f.read())

decode_section = {
    0x80001: decode_soft_node_regions,
    0x80002: dump_unknown_section,
}

def decode_soft(f):
    num_sections, = struct.unpack('<I', f.read(4))
    for i in range(num_sections):
        section_type, section_len = struct.unpack('<2I', f.read(8))
        decode_section[section_type](io.BytesIO(f.read(section_len - 8)))

    assert(not f.read())

def main():
    for arg in sys.argv[1:]:
        decode_soft(open(arg, 'rb'))

if __name__ == '__main__':
    main()
