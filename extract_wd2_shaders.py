#!/usr/bin/env python3

import sys, os, struct, itertools, io, codecs
import generic_shader_extractor
import dx11shaderanalyse

def repeat_extend(s, target_length):
    '''
    Expands (or shrinks) a string to an arbitrary length by repeating it.
    '''
    return s*(target_length // len(s)) + s[:target_length % len(s)]

processed = set()

def lz4_decompress(file):
    # FIXME: Refactor back into the Unity version. This version includes a bit
    # more functionality than the Unity version that we will need to be careful
    # doesn't break the Unity LZ4 decompressor - it supports repeating
    # characters then the match length is greater than the match offset
    # (probably harmless to add to the Unity version), gets the filesize from
    # the DXBC header and supports extended match offset fields (this is risky)
    decoded = bytearray()
    header = None

    for i in itertools.count():
        if header is None and len(decoded) >= 0x20:
            header_off = decoded.find(b'DXBC')
            if header_off != -1 and len(decoded) - header_off >= 0x20:
                header = dx11shaderanalyse.parse_dxbc_header(io.BytesIO(decoded[header_off : header_off + 0x20]))
                # print('Found DXBC header at offset 0x%x' % header_off)
                header_hash = codecs.encode(header.hash, 'hex').decode('ascii')
                if header_hash in processed:
                    print('Skipping previously seen shader %s[%s]' % (header_hash[:16], header_hash[16:]))
                    return None, None, None

        file_offset = file.tell()
        decoded_offset = len(decoded)
        (token,) = struct.unpack('B', file.read(1))

        num_literals = token >> 4
        if num_literals == 15:
            while True:
                (tmp,) = struct.unpack('B', file.read(1))
                num_literals += tmp
                if tmp != 255:
                    break
        tmp = file.read(num_literals)
        assert(len(tmp) == num_literals)
        decoded.extend(tmp)

        if header is not None and len(decoded) >= header.size + header_off:
            return decoded[header_off : header.size + header_off], header, header_hash

        (match_offset,) = struct.unpack('<H', file.read(2))
        if (match_offset & 0xe000) == 0xe000:
            # High three bits set mean this field is extended. Possible
            # WATCH_DOGS2 extension to LZ4? Or something standard I just
            # haven't seen documented?

            # Presumably this field could overflow a second time or more, and
            # presumably the high bits will indicate this, but I'm not positive
            # if it would still be the same three high bits, so catch any
            # values higher than we have seen and we will analyse it then:
            tmp = file.read(1)[0]
            # print('NOTICE: match_offset field extension byte: 0x%02x' % tmp)
            assert(tmp <= 0x04)
            match_offset += tmp << 13

        match_len = (token & 0xf) + 4
        if match_len == 19:
            while True:
                (tmp,) = struct.unpack('B', file.read(1))
                match_len += tmp
                if tmp != 255:
                    break

        #print('chunk %i, file_offset: 0x%x, decoded_offset: 0x%x, literals: %d, match_offset: 0x%04x, match_len: %d' %
        #        (i, file_offset, decoded_offset, num_literals, match_offset, match_len))
        assert(match_offset != 0)
        assert(match_offset <= len(decoded))

        # len()- is necessary here since match_offset may equal match_len
        if match_offset:
            tmp = decoded[-match_offset : len(decoded) - match_offset + match_len]
        else:
            tmp = bytearray([0] * match_len)
        if len(tmp) < match_len:
            rep = itertools.cycle(tmp)
            rep = [ next(rep) for _ in range(match_len - len(tmp))]
            #print('NOTICE: Match length %d > match offset %d, repeating %d bytes from offset 0x%x:\n\t%s' \
            #        % (match_len, match_offset, match_len - len(tmp), len(decoded), rep))
            tmp.extend(rep)
        assert(len(tmp) == match_len)
        tmp = repeat_extend(tmp, match_len)
        decoded.extend(tmp)
    assert(False)

def decode_lz4_at(file, offset):
    # print('Trying to decode lz4 stream at 0x%x...' % offset)
    file.seek(offset)
    shader, header, header_hash = lz4_decompress(file)
    if not shader:
        return False

    hash_embedded = dx11shaderanalyse.shader_hash(shader[20:])
    if hash_embedded != header_hash:
        print('Hash mismatch, Embedded: %s Calculated: %s' % (header_hash, hash_embedded))
        return False

    shader_model = generic_shader_extractor.determine_shader_model(io.BytesIO(shader), 0, header)

    print('0x%08x: Found LZ4 compressed shader %s[%s]' % (offset, header_hash[:16], header_hash[16:]))

    generic_shader_extractor.save_shader_embedded(shader, header_hash, shader_model)

    processed.add(header_hash)

    return True

def try_decoding_range(file, start_offset, end_offset, step):
    for offset in range(start_offset, end_offset, step):
        try:
            if decode_lz4_at(file, offset):
                return True
        except AssertionError as e:
            #print(e.__class__.__name__)
            pass
    else:
        print('No valid LZ4 streams found between offsets 0x%x and 0x%x' % (start_offset, end_offset))

if __name__ == '__main__':
    file = open(sys.argv[1], 'rb')
    if len(sys.argv) >= 3:
        if sys.argv[2].lower().startswith('0x'):
            offset = int(sys.argv[2], 16)
        else:
            offset = int(sys.argv[2])
        if len(sys.argv) >= 4:
            if sys.argv[3].lower().startswith('0x'):
                end_offset = int(sys.argv[3], 16)
            else:
                end_offset = int(sys.argv[3])
            try_decoding_range(file, offset, end_offset)
        else:
            print('Attempting to decompress lz4 stream starting at 0x%x' % offset)
            decode_lz4_at(file, offset)
    else:
        off = -1
        while True:
            off = generic_shader_extractor.stream_search(file, b'DXBC', off + 1)
            if off == -1:
                sys.exit(0)
            try_decoding_range(file, off - 1, off - 0x30, -1)
