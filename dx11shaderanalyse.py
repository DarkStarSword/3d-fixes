#!/usr/bin/env python3

import sys, os, argparse
import struct, hashlib, codecs
from collections import namedtuple

# FIXME: This is per-shader type
system_values = {
    0: 'NONE', # TARGET/COVERAGE/DEPTH/DEPTHGE/DEPTHLE/...
    1: 'POS',
    2: 'CLIPDST',
    3: 'CULLDST',
    4: 'RTINDEX',
    5: 'VPINDEX',
    6: 'VERTID',
    7: 'PRIMID',
    8: 'INSTID',
    9: 'FFACE',
    10: 'SAMPLE',
    11: 'QUADEDGE',
    12: 'QUADINT',
    13: 'TRIEDGE',
    14: 'TRIINT',
}

types = {
    1: 'uint',
    2: 'int',
    3: 'float'
}

def lookup(id, dict):
    return dict.get(id, "Unknown ({})".format(id))

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
        (semantic_off, index, sv, type, reg_num, mask, used, u6) = \
                struct.unpack('<5I2BH', buf[offset:offset+24])
        semantic = c_str(buf[semantic_off:])

        io = output and 'output' or 'input'
        reg_prefix = output and 'o' or 'v'
        print('    dcl_{} {}{}{} : {}{}'.format(
            io, reg_prefix, reg_num, reg_mask(mask), semantic, index or '')) # WIP

        pr_verbose('      |     Semantic: {}'.format(semantic))

        pr_verbose('      |        Index: {}'.format(index))

        # Not all semantics have an obvious system value, e.g. SV_Target uses
        # NONE, and SV_Position uses POS as an output from the VS and input to
        # the PS, but NONE when it's an input to the VS
        pr_verbose('      | System Value: {} ({})'.format(lookup(sv, system_values), sv))
        assert sv in system_values

        pr_verbose('      |         Type: {}'.format(lookup(type, types)))
        assert type in types

        pr_verbose('      |     Register: {}'.format(reg_num))
        # assert(reg == reg_num) # Too strict - the register number may be
        # reused so long as the mask is non-overlapping

        # Mask / used is a bit funky - used is often blank in outputs, sometimes not a subset of mask?
        pr_verbose('      |         Mask: {} (0x{:x})'.format(mask_str(mask), mask), verbosity=1)
        pr_verbose('      |         Used: {} (0x{:x})'.format(mask_str(used), used), verbosity=1)
        pr_verbose('      |    Unknown 6: {:#x}'.format(u6))
        # if output:
        #     assert(used & mask == 0)
        assert(u6 == 0)

    # print('    \\' + r'-'*13)

def decode_isgn(buf):
    return decode_sgn(buf, False)

def decode_osgn(buf):
    return decode_sgn(buf, True)

def decode_pcsg(buf): # Used in domain shaders
    return decode_sgn(buf, True)

chunks = {
    b'ISGN': decode_isgn, # "Input signature"
    b'OSGN': decode_osgn, # "Output signature"
    b'PCSG': decode_pcsg, # "Patch Constant signature", for domain shaders
    # TODO: 'SHEX' / 'SHDR', maybe 'STAT', etc.
}

def get_chunk_info(stream, offset):
    stream.seek(offset)
    (signature, size) = struct.unpack('<4sI', stream.read(8))
    return (signature, size)

def decode_chunk_at(stream, offset):
    (signature, size) = get_chunk_info(stream, offset)
    if verbosity >= 1:
        print("{} chunk at 0x{:08x} size {}".format(signature.decode('ASCII'), offset, size))
    elif verbosity >= 0:
        print(signature.decode('ASCII'))
    if signature in chunks:
        chunks[signature](stream.read(size))

def get_chunk(stream, name):
    header = parse_dxbc_header(stream)
    chunk_offsets = get_chunk_offsets(stream, header)
    for idx in range(header.chunks):
        (signature, size) = get_chunk_info(stream, chunk_offsets[idx])
        if signature == name:
            return stream.read(size)

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

# vi: et sw=4:ts=4
