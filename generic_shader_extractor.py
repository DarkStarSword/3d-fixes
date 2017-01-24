#!/usr/bin/env python3

import os, argparse, mmap, codecs, sys
import dx11shaderanalyse, extract_unity_shaders

dx11shaderanalyse.verbosity = -1

target_dir_3dmigoto = 'ShaderCache3DMigoto'
target_dir_embedded = 'ShaderCacheEmbedded'
target_dir_bytecode = 'ShaderCacheBytecode'

blacklist_dirs = [
    'shadercache',
    'shaderfixes',
    'shaderoverride',
    'dumps',
    'extracted',
    'shadercrcs',
    'shaderfnvs',
    target_dir_3dmigoto.lower(),
    target_dir_embedded.lower(),
    target_dir_bytecode.lower(),
]

blacklist_files = ['d3d11.dll', 'd3dcompiler_46.dll']

def _save_shader(shader, dir, filename):
    if not os.path.isdir(dir):
        os.mkdir(dir)
    path = os.path.join(dir, filename)
    bin_path = path + '.bin'
    if os.path.isfile(bin_path):
        # Skip extraction if the binary has already been extracted
        return
    inter_hlsl_path = path + '.hlsl'
    final_hlsl_path = path + '_replace.txt'
    inter_asm_path = path + '.asm'
    final_asm_path = path + '.txt'
    with open(bin_path, 'wb') as f:
        f.write(shader)
    if args is not None and not args.only_bin:
        extract_unity_shaders.disassemble_and_decompile_binary_shader(bin_path)
    if os.path.isfile(inter_asm_path):
        os.rename(inter_asm_path, final_asm_path)
    if os.path.isfile(inter_hlsl_path):
        os.rename(inter_hlsl_path, final_hlsl_path)

def save_shader_embedded(shader, hash_embedded, shader_model):
    _save_shader(shader, target_dir_embedded, '%s-%s' % (hash_embedded[:16], shader_model[:2]))

def save_shader(shader, shader_model, hash_3dmigoto, hash_embedded, hash_bytecode):
    if args.hash == '3dmigoto':
        _save_shader(shader, target_dir_3dmigoto, '%016x-%s' % (hash_3dmigoto, shader_model[:2]))

    if args.hash == 'embedded':
        save_shader_embedded(shader, hash_embedded, shader_model)

    if args.hash == 'bytecode':
        _save_shader(shader, target_dir_bytecode, '00000000%08x-%s' % (hash_bytecode, shader_model[:2]))

def print_parse_error(e, desc):
    if e.__class__ == AssertionError:
        import traceback
        print('  %s %s: ' % (e.__class__.__name__, desc), end='')
        # Python 3.5 supports negative limit to simplify this:
        stack = traceback.extract_tb(e.__traceback__)
        print(traceback.format_list(stack[-1:])[0].strip())
    else:
        print('  %s %s: %s' % (e.__class__.__name__, desc, str(e)))

def stream_search(stream, target, off):
    stream.seek(off)
    # Align first read to next page boundary for maximum speed:
    block_size = mmap.PAGESIZE - off % mmap.PAGESIZE
    buf = b''
    while True:
        new_buf = stream.read(block_size)
        if not new_buf:
            return -1
        buf = buf[-len(target) + 1:] + new_buf
        result = buf.find(target)
        if result != -1:
            off = stream.tell() - len(buf) + result
            stream.seek(off)
            return off
        # Subsequent reads use the page size for maximum speed:
        block_size = mmap.PAGESIZE

def determine_shader_model(fp, off, header, chunk_offsets=None):
    try:
        if chunk_offsets is None:
            fp.seek(off + 0x20)
            chunk_offsets = dx11shaderanalyse.get_chunk_offsets(fp, header)
        for idx in range(header.chunks):
            shader_model = dx11shaderanalyse.check_chunk_for_shader_model(fp, off + chunk_offsets[idx])
            if shader_model is not None:
                return shader_model
        else:
            print('No shader model found - missing bytecode section?')
            return 'xx_x_x'
    except Exception as e:
        print_parse_error(e, 'while trying to determine shader model')
        return 'xx_x_x'

processed = set()

def search_file(path):
    print('Searching %s' % path)
    with open(path, 'rb') as fp:
        off = -1
        while True:
            off = stream_search(fp, b'DXBC', off + 1)
            if off == -1:
                return
            try:
                header = dx11shaderanalyse.parse_dxbc_header(fp)

                header_hash = codecs.encode(header.hash, 'hex').decode('ascii')
                if header_hash in processed:
                    print('%s+%08x: *skip* embedded: %s[%s] seen before' %
                        (path, off, header_hash[:16], header_hash[16:]))
                    if not args.skip_hash_check:
                        # Skipping over the shader's claimed size is a little
                        # risky since we haven't validated the embedded hash
                        # yet, but the chance that we find an invalid shader
                        # with a seemingly valid header and a hash that we have
                        # previously validated is so low that I deem the risk
                        # acceptable and the speed benefits worthwhile. Don't
                        # skip over it if --skip-hash-check was specified
                        # though, as that is more risky:
                        off += header.size - 1
                    continue

                bak = fp.tell()
                fp.seek(off)
                shader = fp.read(header.size)
                assert(len(shader) == header.size)
                fp.seek(bak)
                if not args.skip_hash_check:
                    hash_embedded = dx11shaderanalyse.shader_hash(shader[20:])
                    if hash_embedded != header_hash:
                        print('Hash mismatch, Embedded: %s Calculated: %s' % (header_hash, hash_embedded))
                        continue

                chunk_offsets = dx11shaderanalyse.get_chunk_offsets(fp, header)
                shader_model = determine_shader_model(fp, off, header, chunk_offsets)

                print('%s+%08x: %s embedded: %s[%s]' %
                    (path, off, shader_model, header_hash[:16], header_hash[16:]), end='')

                if args.hash == '3dmigoto':
                    hash_3dmigoto = extract_unity_shaders.fnv_3Dmigoto_shader(shader)
                    print(' 3dmigoto: %016x' % hash_3dmigoto, end='')
                else:
                    hash_3dmigoto = None

                if args.hash == 'bytecode' and crcmod is not None:
                    hash_bytecode = 0
                    for idx in range(header.chunks):
                        hash_bytecode = dx11shaderanalyse.calc_chunk_bytecode_hash(fp, off + chunk_offsets[idx], hash_bytecode)
                    print(' bytecode: %08x' % hash_bytecode, end='')
                else:
                    hash_bytecode = None
                print()

                save_shader(shader, shader_model, hash_3dmigoto, header_hash, hash_bytecode)

                processed.add(header_hash)
                if not args.skip_hash_check:
                    # If we verified the hash and extracted a shader we can be
                    # pretty sure there won't be another overlapping it:
                    off += header.size - 1

            except Exception as e:
                print_parse_error(e, 'while parsing possible shader')
                continue

args = None
def parse_args():
    global args, crcmod
    parser = argparse.ArgumentParser(description = 'Generic Shader Extraction Tool')
    parser.add_argument('paths', nargs='*',
            help='List of files or directories to search for shader binaries')
    parser.add_argument('--hash', choices=['embedded', '3dmigoto', 'bytecode'], required=True)
    parser.add_argument('--blacklist', action='append', default=[],
            help='Skip these file or directory names')
    parser.add_argument('--only-bin', action='store_true',
            help='Do not disassemble or decompile extracted shaders')
    parser.add_argument('--skip-hash-check', action='store_true',
            help='Do not verify the embedded hash in each shader. Faster, but may extract some garbage')
    args = parser.parse_args()

    try:
        import crcmod
    except ImportError:
        print('Python crcmod is not installed - bytecode hash is unavailable. Install with:')
        print('python3 -m ensurepip')
        print('python3 -m pip install crcmod')
        if args.hash == 'bytecode':
            sys.exit(1)
        crcmod = None

    for path in map(os.path.basename, args.blacklist):
        blacklist_dirs.append(path.lower())
        blacklist_files.append(path.lower())


def main():
    parse_args()

    # Windows command prompt passes us a literal *, so expand any that we were passed:
    import glob
    paths = []
    for path in args.paths:
        if '*' in path:
            paths.extend(glob.glob(path))
        else:
            paths.append(path)

    if not paths:
        paths = ('.', )

    for path in paths:
        if os.path.isfile(path):
            search_file(path)
            continue

        for (dirpath, dirnames, filenames) in os.walk(path):
            # print('Walking %s...' % dirpath)
            for dirname in dirnames[:]:
                if dirname.lower() in blacklist_dirs:
                    print('Skipping blacklisted directory: %s' % os.path.join(dirpath, dirname))
                    dirnames.remove(dirname)

            for filename in filenames:
                if filename.lower() in blacklist_files:
                    print('Skipping blacklisted file: %s' % os.path.join(dirpath, filename))
                    continue
                search_file(os.path.join(dirpath, filename))

if __name__ == '__main__':
    main()
