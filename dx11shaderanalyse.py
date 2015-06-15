#!/usr/bin/env python3

import sys, os, argparse
import struct, hashlib, codecs
from collections import namedtuple

def pr_verbose(*a, verbosity=1, **kw):
    if globals()['verbosity'] >= verbosity:
        print(*a, **kw)

def parse_dxbc_header(stream):
    DXBCHeader = namedtuple('DXBCHeader',
            ['signature', 'hash', 'unknown1', 'size', 'chunks'])
    header = DXBCHeader(*struct.unpack('<4s16s3I', stream.read(0x20)))
    assert(header.signature == b'DXBC')
    assert(header.unknown1 == 1)
    return header

def get_chunk_offsets(stream, header):
    return struct.unpack('<{}I'.format(header.chunks), stream.read(4 * header.chunks))

def c_str(buf):
    return buf[:buf.find(b'\0')].decode('ascii')

# def get_SysValue_name(val):
#     return {
#         0: 'NONE',
#         1: 'POS'
#     }.get(val, 'UNKNOWN')

def mask_components(mask):
    r = [' ']*4
    assert((mask & ~0xf) == 0)
    if mask & 0x1: r[0] = 'x'
    if mask & 0x2: r[1] = 'y'
    if mask & 0x4: r[2] = 'z'
    if mask & 0x8: r[3] = 'w'
    return r

def mask_str(mask):
    return ''.join(mask_components(mask)).rstrip()

def reg_mask(mask):
    # Cleaner output, but does not match MS's disassembler:
    if mask == 0 or mask == 0xf:
    # Less clean:
    # if mask == 0:
        return ''
    return '.' + ''.join(filter(lambda x: x != ' ' and x or None, mask_components(mask)))

def decode_sgn(buf, output):
    (num_regs, u1) = struct.unpack('<2I', buf[0:8])
    pr_verbose('  Registers: {}'.format(num_regs))
    pr_verbose('  Unknown 1: {:#x}'.format(u1))
    assert(u1 == 8)
    for reg in range(num_regs):
        offset = 8 + 24*reg # Is the 8 offset from u1?
        (semantic_off, index, u3, u4, reg_num, mask, used, u6) = \
                struct.unpack('<5I2BH', buf[offset:offset+24])
        semantic = c_str(buf[semantic_off:])

        io = output and 'output' or 'input'
        reg_prefix = output and 'o' or 'v'
        print('    dcl_{} {}{}{} : {}{}'.format(
            io, reg_prefix, reg_num, reg_mask(mask), semantic, index or '')) # WIP

        pr_verbose('      |  Semantic: {}'.format(semantic))

        pr_verbose('      |     Index: {}'.format(index))

        # Seems right for texcoords & pos, but not for SV_Target:
        # Could have a different meaning for inputs / outputs?
        # print('      |  SysValue: {}'.format(get_SysValue_name(u3)))
        pr_verbose('      | Unknown 3: {:#x}'.format(u3))
        if semantic == 'SV_POSITION' or semantic == 'SV_Position':
            assert(u3 == 1)
        elif semantic == 'SV_VertexID':
            assert(u3 == 6)
        else:
            assert(u3 == 0)

        pr_verbose('      | Unknown 4: {:#x}'.format(u4))
        if semantic == 'SV_VertexID':
            assert(u4 == 1)
        else:
            assert(u4 == 3)

        pr_verbose('      |  Register: {}'.format(reg_num))
        # assert(reg == reg_num) # Too strict - the register number may be
        # reused so long as the mask is non-overlapping

        # Mask / used is a bit funky - used is often blank in outputs, sometimes not a subset of mask?
        pr_verbose('      |      Mask: {}'.format(mask_str(mask)).rstrip(), verbosity=1)
        pr_verbose('      |      Used: {}'.format(mask_str(used)).rstrip(), verbosity=1)
        pr_verbose('      | Unknown 6: {:#x}'.format(u6))
        # if output:
        #     assert(used & mask == 0)
        assert(u6 == 0)

    # print('    \\' + r'-'*13)

def decode_isgn(buf):
    return decode_sgn(buf, False)

def decode_osgn(buf):
    return decode_sgn(buf, True)

chunks = {
    b'ISGN': decode_isgn,
    b'OSGN': decode_osgn,
    # TODO: 'SHEX' / 'SHDR', maybe 'STAT', etc.
}

def decode_chunk_at(stream, offset):
    stream.seek(offset)
    (signature, size) = struct.unpack('<4sI', stream.read(8))
    if verbosity >= 1:
        print("{} chunk at 0x{:08x} size {}".format(signature.decode('ASCII'), offset, size))
    elif verbosity >= 0:
        print(signature.decode('ASCII'))
    if signature in chunks:
        chunks[signature](stream.read(size))

def brute_hash(stream):
    # Try MD5 on every possible subset of the file to see if it matches anything
    # Despite the algorithm looking *VERY* similar to MD5, I don't get a match
    size = os.fstat(stream.fileno()).st_size
    for i in range(0, size, 1):
        for j in range(size, i, -1):
            stream.seek(i)
            print(i, j, j-1, hashlib.md5(stream.read(j - i)).hexdigest())

def parse(stream):
    header = parse_dxbc_header(stream)
    pr_verbose(header, verbosity=2)
    chunk_offsets = get_chunk_offsets(stream, header)

    # A few experiments on the hash:
    pr_verbose('Embedded hash:', codecs.encode(header.hash, 'hex').decode('ascii'))
    # stream.seek(20)
    # print('MD5sum:', hashlib.md5(stream.read(header.size - 20)).hexdigest())
    # brute_hash(stream)

    for idx in range(header.chunks):
        decode_chunk_at(stream, chunk_offsets[idx])

def parse_args():
    global args, verbosity

    parser = argparse.ArgumentParser(description = 'DX11 Shader Binary Analysis Tool')
    parser.add_argument('files', nargs='+',
            help='List of shader binary files to process')
    parser.add_argument('--verbose', '-v', action='count', default=0,
            help='Level of verbosity')
    parser.add_argument('--quiet', '-q', action='count', default=0,
            help='Surpress informational messages')
    args = parser.parse_args()
    verbosity = args.verbose - args.quiet

def main():
    parse_args()
    for filename in args.files:
        print('\nparsing {}...'.format(filename))
        parse(open(filename, 'rb'))

if __name__ == '__main__':
    sys.exit(main())
