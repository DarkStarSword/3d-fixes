#!/usr/bin/env python3

import sys, os, argparse
import struct, hashlib, codecs, zlib
from collections import namedtuple
import numpy as np
import math
import extract_unity_shaders
import io

system_values = {
    0: 'NONE', # or TARGET, or SPRs: COVERAGE, DEPTH, DEPTHGE, DEPTHLE, ...
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
    15: 'LINEDET',
    16: 'LINEDEN',
}

types = {
    1: 'uint',
    2: 'int',
    3: 'float'
}

verbosity = 0

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

def decode_sgn(buf, output, size=24):
    (num_regs, u1) = struct.unpack('<2I', buf[0:8])
    pr_verbose('  Registers: {}'.format(num_regs))
    pr_verbose('  Unknown 1: {:#x}'.format(u1))
    assert(u1 == 8)
    stream = min_precision = None
    for reg in range(num_regs):
        offset = 8 + size*reg # Is the 8 offset from u1?

        if size == 24:
            (semantic_off, index, sv, type, reg_num, mask, used, u6) = \
                    struct.unpack('<5I2BH', buf[offset:offset+size])
        elif size == 28: # OSG5
            (stream, semantic_off, index, sv, type, reg_num, mask, used, u6) = \
                    struct.unpack('<6I2BH', buf[offset:offset+size])
        elif size == 32: # ISG1, OSG1, PSG1
            (stream, semantic_off, index, sv, type, reg_num, mask, used, u6, min_precision) = \
                    struct.unpack('<6I2BHI', buf[offset:offset+size])
        else:
            assert(False) #BUG

        semantic = c_str(buf[semantic_off:])

        io = output and 'output' or 'input'
        reg_prefix = output and 'o' or 'v'
        pr_verbose('    dcl_{} {}{}{} : {}{}'.format(
            io, reg_prefix, reg_num, reg_mask(mask), semantic, index or ''), verbosity=0) # WIP

        if stream is not None:
            pr_verbose('      |       Stream: {}'.format(stream))

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

        if min_precision is not None:
            pr_verbose('      |Min Precision: {}'.format(min_precision))

        # Mask / used is a bit funky - used is often blank in outputs, sometimes not a subset of mask?
        pr_verbose('      |         Mask: {} (0x{:x})'.format(mask_str(mask), mask), verbosity=1)
        pr_verbose('      |         Used: {} (0x{:x})'.format(mask_str(used), used), verbosity=1)
        pr_verbose('      |    Unknown 6: {:#x}'.format(u6))
        # if output:
        #     assert(used & mask == 0)
        assert(u6 == 0)

    # print('    \\' + r'-'*13)

def decode_isgn(buf): return decode_sgn(buf, False, 24)
def decode_isg1(buf): return decode_sgn(buf, False, 32)
def decode_osgn(buf): return decode_sgn(buf, True, 24)
def decode_osg1(buf): return decode_sgn(buf, True, 32)
def decode_osg5(buf): return decode_sgn(buf, True, 28)
def decode_pcsg(buf): return decode_sgn(buf, True, 24)
def decode_psg1(buf): return decode_sgn(buf, True, 32)

shader_types = {
    0: 'ps',
    1: 'vs',
    2: 'gs',
    3: 'hs',
    4: 'ds',
    5: 'cs',
}

def get_shader_model_section(buf, verify_major = None):
    version, shader_type = struct.unpack('<2H', buf[:4])
    shader_type = shader_types[shader_type]
    major = version >> 4
    minor = version & 0xf
    if verify_major is not None:
        assert(major == verify_major)
    shader_model = ('{}_{}_{}'.format(shader_type, major, minor))
    pr_verbose('    {}'.format(shader_model), verbosity=0)
    return shader_model

def get_shader_model_shdr(buf):
    return get_shader_model_section(buf, 4)
def get_shader_model_shex(buf):
    return get_shader_model_section(buf, 5)

chunks = {
    b'ISGN': decode_isgn, # "Input signature"
    b'ISG1': decode_isg1,
    b'OSGN': decode_osgn, # "Output signature"
    b'OSG1': decode_osg1,
    b'OSG5': decode_osg5,
    b'PCSG': decode_pcsg, # "Patch Constant signature", for domain shaders
    b'PSG1': decode_psg1,
    b'SHEX': get_shader_model_shex,
    b'SHDR': get_shader_model_shdr,
    # TODO: 'SHEX' / 'SHDR', maybe 'STAT', etc.
}

shader_model_sections = {
    b'SHEX': get_shader_model_shex,
    b'SHDR': get_shader_model_shdr,
}

def get_chunk_info(stream, offset):
    stream.seek(offset)
    (signature, size) = struct.unpack('<4sI', stream.read(8))
    return (signature, size)

hash_sections = (
	b"SHDR", b"SHEX",          # Bytecode
	b"ISGN",          b"ISG1", # Input signature
	b"PCSG",          b"PSG1", # Patch constant signature
	b"OSGN", b"OSG5", b"OSG1", # Output signature
)

def _calc_chunk_bytecode_hash(signature, buf, bytecode_hash):
    if signature in hash_sections:
        # crc32c is not available in Python's standard libraries yet, use crcmod:
        import crcmod.predefined
        bytecode_hash = crcmod.predefined.mkPredefinedCrcFun("crc-32c")(buf, bytecode_hash)
    return bytecode_hash

def calc_chunk_bytecode_hash(stream, offset, bytecode_hash):
    # Called from generic_shader_extractor
    (signature, size) = get_chunk_info(stream, offset)
    buf = stream.read(size)
    return _calc_chunk_bytecode_hash(signature, buf, bytecode_hash)

def decode_chunk_at(stream, offset, bytecode_hash):
    (signature, size) = get_chunk_info(stream, offset)
    buf = stream.read(size)
    if verbosity >= 1:
        print("{} chunk at 0x{:08x} size {}".format(signature.decode('ASCII'), offset, size))
    elif verbosity >= 0 or bytecode_hash is not None:
        print('{}'.format(signature.decode('ASCII')))
    if signature in chunks:
        chunks[signature](buf)
    if bytecode_hash is not None:
        return _calc_chunk_bytecode_hash(signature, buf, bytecode_hash)

def check_chunk_for_shader_model(stream, offset):
    (signature, size) = get_chunk_info(stream, offset)
    if signature in shader_model_sections:
        return shader_model_sections[signature](stream.read(size))

def get_chunk(stream, name):
    header = parse_dxbc_header(stream)
    chunk_offsets = get_chunk_offsets(stream, header)
    for idx in range(header.chunks):
        (signature, size) = get_chunk_info(stream, chunk_offsets[idx])
        if signature == name:
            return stream.read(size)

def shader_hash(message, real_md5=False):
    '''
    Follows the MD5 psuedocode from:
      https://en.wikipedia.org/wiki/Md5

    If real_md5=False, will use a slight modification to the padding method to
    generate the same obfuscated MD5 hashes as d3dcompiler.
    '''

    np.seterr(over='ignore')

    message = bytearray(message)

    # leftrotate function definition
    def leftrotate (x, c):
        return np.uint32(x << c) | np.uint32(x >> (32-c))

    # Gotcha: length is in bits, not bytes:
    orig_len_bytes = len(message)
    orig_len_bits = np.uint64(orig_len_bytes * 8)

    # Note: All variables are unsigned 32 bit and wrap modulo 2^32 when calculating

    # s specifies the per-round shift amounts
    s = [7, 12, 17, 22]*4 + [5, 9, 14, 20]*4 + [4, 11, 16, 23]*4 + [6, 10, 15, 21]*4

    # Use binary integer part of the sines of integers (Radians) as constants:
    K = [ np.uint32(math.floor(2**32 * abs(math.sin(i)))) for i in range(1, 65) ]

    # Initialize variables:
    a0 = np.uint32(0x67452301) # A
    b0 = np.uint32(0xefcdab89) # B
    c0 = np.uint32(0x98badcfe) # C
    d0 = np.uint32(0x10325476) # D

    # Pre-processing: adding a single 1 bit
    # append "1" bit to message /* Notice: the input bytes are considered as bits
    # strings, where the first bit is the most significant bit of the byte.
    message.append(0x80)

    # Pre-processing: padding with zeros
    # append "0" bit until message length in bits ≡ 448 (mod 512)
    pad = 64 - (len(message) % 64)
    if pad < 8:
        message.extend([0] * (64 + pad - 8))
    else:
        message.extend([0] * (pad - 8))

    # append original length in bits mod (2 pow 64) to message

    # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    # XXX
    # XXX MS Implementation differs from RSA MD5 only in the way the size is
    # XXX used to pad the final block.
    # XXX
    # XXX The Real MD5 Implementation would use:
    # XXX     message.extend(struct.pack('<Q', orig_len_bits)) # 64bit size
    # XXX
    # XXX But here they *insert* that at the *start* of the final 512bit block
    # XXX as a *32bit* little-endian value, and add a second *31bit* size in
    # XXX *bytes* at the end of the block shifted left with a final 1 added.
    # XXX
    # XXX I was wondering if they had simply made an error when implementing
    # XXX it, however, while standards can be hard to read and the reference
    # XXX implementation is needlessly complex - the part on padding with the
    # XXX size is pretty damn clear, and this is a little too bizzare to be by
    # XXX accident. Therefore, it appears they intentionally obfuscated it, for
    # XXX whatever pointless and misguided reason they thought they had.
    # XXX
    # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

    if real_md5:
        message.extend(struct.pack('<Q', orig_len_bits))
    else:
        message = message[:-56] + struct.pack('<I', orig_len_bits) + message[-56:]
        message.extend(struct.pack('<I', (orig_len_bytes << 1) | 1))

    assert(len(message) % 64 == 0)

    # Process the message in successive 512-bit chunks:
    # for each 512-bit chunk of message
    while message:
        # break chunk into sixteen 32-bit words M[j], 0 ≤ j ≤ 15
        M = struct.unpack('<16I', message[:64])
        message = message[64:]

        # Initialize hash value for this chunk:
        A = a0
        B = b0
        C = c0
        D = d0

        # Main loop:
        for i in range(64):
            if i < 16:
                F = (B & C) | (~B & D)
                g = i
            elif i < 32:
                F = (D & B) | (~D & C)
                g = np.uint32((5*i + 1) % 16)
            elif i < 48:
                F = B ^ C ^ D
                g = np.uint32((3*i + 5) % 16)
            else:
                F = C ^ (B | ~D)
                g = np.uint32((7*i) % 16)
            dTemp = D
            D = C
            C = B
            B = np.uint32(B + leftrotate(np.uint32(A + F + K[i] + M[g]), s[i]))
            A = dTemp

        # Add this chunk's hash to result so far:
        a0 = np.uint32(a0 + A)
        b0 = np.uint32(b0 + B)
        c0 = np.uint32(c0 + C)
        d0 = np.uint32(d0 + D)

    # var char digest[16] := a0 append b0 append c0 append d0 //(Output is in little-endian)
    return '%08x%08x%08x%08x' % struct.unpack('>4I', struct.pack('<4I', a0, b0, c0, d0))

def parse(stream):
    if getattr(args, '3dmigoto_hash'):
        stream = io.BytesIO(stream.read())
        migoto_hash = extract_unity_shaders.fnv_3Dmigoto_shader(stream.getbuffer())
        print('3DMigoto hash: %016x' % migoto_hash)

    header = parse_dxbc_header(stream)
    pr_verbose(header, verbosity=2)
    chunk_offsets = get_chunk_offsets(stream, header)

    pr_verbose('Embedded hash:', codecs.encode(header.hash, 'hex').decode('ascii'))
    if args.hash:
        stream.seek(20)
        print('Header size:', header.size)
        hashable = stream.read(header.size - 20)
        assert(len(hashable) + 20 == header.size)
        # print('       MD5sum:', hashlib.md5(stream.read(header.size - 20)).hexdigest())
        print('    DXBC hash:', shader_hash(hashable))

    bytecode_hash = None
    if args.bytecode_hash:
        bytecode_hash = 0
    for idx in range(header.chunks):
        bytecode_hash = decode_chunk_at(stream, chunk_offsets[idx], bytecode_hash)
    if args.bytecode_hash:
        print('Bytecode hash: %08x' % bytecode_hash)

def parse_args():
    global args, verbosity

    parser = argparse.ArgumentParser(description = 'DX11 Shader Binary Analysis Tool')
    parser.add_argument('files', nargs='+',
            help='List of shader binary files to process')
    parser.add_argument('--verbose', '-v', action='count', default=0,
            help='Level of verbosity')
    parser.add_argument('--quiet', '-q', action='count', default=0,
            help='Surpress informational messages')
    parser.add_argument('--hash', action='store_true',
            help='Calculate the obfuscated MD5-like hash used by DX shaders')
    parser.add_argument('--bytecode-hash', action='store_true',
            help='Calculate the bytecode+signature hash, e.g. use to correlate shaders that only differ by debug info, etc.')
    parser.add_argument('--3dmigoto-hash', action='store_true',
            help='Calculate the default hash used by 3DMigoto')
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
