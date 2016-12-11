#!/usr/bin/env python3

import os, argparse, mmap, codecs, sys
import dx11shaderanalyse, extract_unity_shaders

dx11shaderanalyse.verbosity = -1

target_dir_3dmigoto = 'ShaderCache3DMigoto'
target_dir_embedded = 'ShaderCacheEmbedded'
target_dir_bytecode = 'ShaderCacheBytecode'

blacklist_dirs = (
    'shadercache',
    'shaderfixes',
    'extracted',
    'shadercrcs',
    'shaderfnvs',
    target_dir_3dmigoto.lower(),
    target_dir_embedded.lower(),
    target_dir_bytecode.lower(),
)

blacklist_files = ('d3d11.dll', 'd3dcompiler_46.dll')

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
    extract_unity_shaders.disassemble_and_decompile_binary_shader(bin_path)
    if os.path.isfile(inter_asm_path):
        os.rename(inter_asm_path, final_asm_path)
    if os.path.isfile(inter_hlsl_path):
        os.rename(inter_hlsl_path, final_hlsl_path)

def save_shader(shader, hash_3dmigoto, hash_embedded, hash_bytecode):
    if args.hash == '3dmigoto':
        _save_shader(shader, target_dir_3dmigoto, '%016x-xx' % hash_3dmigoto)

    if args.hash == 'embedded':
        _save_shader(shader, target_dir_embedded, '%s-xx' % hash_embedded[:16])

    if args.hash == 'bytecode':
        _save_shader(shader, target_dir_bytecode, '00000000%08x-xx' % hash_bytecode)

def search_file(path):
    print('Searching %s' % path)
    with open(path, 'rb') as fp:
        with mmap.mmap(fp.fileno(), 0, access = mmap.ACCESS_READ) as mm:
            off = -1
            while True:
                off = mm.find(b'DXBC', off + 1)
                if off == -1:
                    return
                mm.seek(off)
                try:
                    header = dx11shaderanalyse.parse_dxbc_header(mm)
                    shader = mm[off : off + header.size]
                    assert(len(shader) == header.size)
                    hash_embedded = dx11shaderanalyse.shader_hash(shader[20:])
                    if hash_embedded == codecs.encode(header.hash, 'hex').decode('ascii'):
                        hash_3dmigoto = extract_unity_shaders.fnv_3Dmigoto_shader(shader)

                        print('%s+%08x: embedded: %s[%s] 3dmigoto: %016x' %
                                (path, off, hash_embedded[:16], hash_embedded[16:], hash_3dmigoto), end='')

                        try:
                            chunk_offsets = dx11shaderanalyse.get_chunk_offsets(mm, header)
                            hash_bytecode = 0
                            for idx in range(header.chunks):
                                hash_bytecode = dx11shaderanalyse.decode_chunk_at(mm, off + chunk_offsets[idx], hash_bytecode)
                            print(' bytecode: %08x' % hash_bytecode, end='')
                        except ImportError:
                            hash_bytecode = None

                        print()
                        save_shader(shader, hash_3dmigoto, hash_embedded, hash_bytecode)
                except Exception as e:
                    print('  %s while parsing possible shader %s' % (e.__class__.__name__, str(e)))
                    raise
                    continue

def parse_args():
    global args
    parser = argparse.ArgumentParser(description = 'Generic Shader Extraction Tool')
    parser.add_argument('paths', nargs='*',
            help='List of files or directories to search for shader binaries')
    parser.add_argument('--hash', choices=['embedded', '3dmigoto', 'bytecode'], required=True)
    args = parser.parse_args()

    if args.hash == 'bytecode':
        try:
            import crcmod
        except ImportError:
            print('Python crcmod is not installed - bytecode hash is unavailable')
            sys.exit(1)

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
