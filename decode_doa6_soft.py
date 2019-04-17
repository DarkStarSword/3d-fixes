#!/usr/bin/env python3

bl_info = {
    "name": "DOA6 Soft Body",
    "author": "Ian Munsie (darkstarsword@gmail.com)",
    "location": "File > Import-Export",
    "description": "Work with DOA6 soft body meshes",
    "category": "Import-Export",
    "tracker_url": "https://github.com/DarkStarSword/3d-fixes/issues",
}

import os, struct, sys, numpy, io, copy, itertools, math, collections, json, argparse, glob

try:
    import bpy
except ImportError as e:
    print('Running standalone - decoding only, no Blender integration')
else:
    import bpy_extras

class Fatal(Exception): pass

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

verbosity = 0
def pr_verbose(*args, **kwargs):
    if verbosity >= 1:
        print(*args, **kwargs)

def decode_node(f, region_obj):
    buf = f.read(10*4)
    node, = numpy.frombuffer(buf, node_fmt)
    pr_verbose('Node', node['id'], node)
    #assert(node['0x43'] == 0x43)

    # Other nodes this one influences and/or is influenced by:
    for i in range(node['links'] + 1):
        data = struct.unpack('<If', f.read(2*4))
        pr_verbose('  Link %i: %.2f' % data)

    data = struct.unpack('<3f3I', f.read(6*4))
    #assert(data == (0,)*6)
    assert(data[3:] == (0,)*3)
    if data != (0,)*6:
        pr_verbose(' ', data[:3])

    if region_obj:
        # Could use other representations or even soft body within Blender, but
        # since we are only after the node positions let's keep it simple and
        # represent each soft body node with a cube:
        bpy.ops.mesh.primitive_cube_add(radius=0.25, location=node['pos'], rotation=node['rot'])
        bpy.context.active_object.name = '%s[%u]' % (region_obj.name, node['id'])
        bpy.context.active_object.lock_location = (True, True, True)
        bpy.context.active_object.lock_rotation = (True, True, True)
        bpy.context.active_object.parent = region_obj

def decode_soft_node_region(f):
    header = struct.unpack('<13I', f.read(13*4))
    (id, len1, z2, z3, u4, len2, len3, root_bone_idx, u6, u7, z8, o9, len4) = header
    pr_verbose('Soft region header', header)

    # Assertions to catch any variants we haven't seen before:
    #assert(header == (0, 217, 0, 0, 9, 217, 58, 100, 1, 3, 0, 1, 217)) # len: 21836, pt2 len: 401*4 (217 + 9 + 1 + 3*58 ?), pt3 len: 494*4
    #assert(header == (1, 217, 0, 0, 9, 217, 58, 101, 1, 3, 0, 1, 217)) # len: 21836, pt2 len: 401*4 (217 + 9 + 1 + 3*58 ?), pt3 len: 494*4
    #assert(header == (4, 104, 0, 0, 9, 104, 58, 102, 0, 1, 0, 1, 104)) # len: 12900, pt2 len: 287*4 (104 + 9 + 0 + 3*58 ?), pt3 len: 268*4
    #assert(header == (5, 104, 0, 0, 9, 104, 70, 103, 0, 1, 0, 1, 104)) # len: 13044, pt2 len: 323*4 (104 + 9 + 0 + 3*70 ?), pt3 len: 268*4
    assert(z2 == 0)
    assert(z3 == 0)
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
    pr_verbose('Soft region unknown', unknown)

    region_obj = None
    if 'bpy' in globals():
        name = '%s.SOFT[%u]' % (os.path.basename(f.name), id)
        region_obj = bpy.data.objects.new(name, None)
        axis_forward = '-Z'; axis_up = 'Y'; # FIXME: use orientation_helper_factory
        conversion_matrix = bpy_extras.io_utils.axis_conversion(from_forward=axis_forward, from_up=axis_up).to_4x4()
        region_obj.matrix_world = conversion_matrix
        bpy.context.scene.objects.link(region_obj)

    for i in range(len1):
        decode_node(f, region_obj)

    # Next follows several lists of node IDs. The length of each list seems to
    # be from various fields in the header, but the contents of the individual
    # lists doesn't matter so much to us so I haven't confirmed that the lists
    # are actually in this order so they might be mixed up (but looks right):
    pr_verbose(numpy.frombuffer(f.read(u4   * 4), numpy.uint32))
    pr_verbose(numpy.frombuffer(f.read(len1 * 4), numpy.uint32))
    pr_verbose(numpy.frombuffer(f.read(u6   * 4), numpy.uint32))
    pr_verbose(numpy.frombuffer(f.read(len3 * 4 * 3), numpy.dtype([('node', numpy.uint32, 3)])))

    # Next follows a list of floats. Conveniently it gives us the section
    # length in bytes that we can skip over:
    (_6, len5) = struct.unpack('<2I', f.read(8))
    pr_verbose(_6)
    #assert(_6 == 6) # KOK_COS_004.g1m has 7
    pr_verbose(numpy.frombuffer(f.read(len5 - 8), numpy.float32))

def decode_soft_node_regions(f):
    num_regions, = struct.unpack('<I', f.read(4))
    for i in range(num_regions):
        decode_soft_node_region(f)
        pr_verbose()

    assert(not f.read())

def print_unknown(name, buf):
    orig_opts = numpy.get_printoptions()
    opts = copy.deepcopy(orig_opts)
    opts['formatter']['int'] = lambda x : '%08x' % x
    numpy.set_printoptions(**opts)

    pr_verbose(name)
    pr_verbose(numpy.frombuffer(buf, numpy.uint32))

    numpy.set_printoptions(**orig_opts)

def dump_unknown_section(f, *args):
    print_unknown('Unknown section:', f.read())

decode_soft_section = {
    0x80001: decode_soft_node_regions,
    0x80002: dump_unknown_section,
}

def io_range(f, len):
    b = io.BytesIO(f.read(len))
    b.name = f.name
    return b

class G1MChunk(object):
    def __init__(self, f, version, g1m):
        self.orig_val = f.getvalue()
        self.version = version
        self.g1m = g1m

    def getvalue(self):
        return self.orig_val

class DumpUnknownG1MChunk(G1MChunk):
    def __init__(self, f, version, g1m):
        G1MChunk.__init__(self, f, version, g1m)
        print_unknown('Unknown section:', f.read())

class SOFTChunk(G1MChunk):
    def __init__(self, f, version, g1m):
        assert(version == b'5100')
        G1MChunk.__init__(self, f, version, g1m)
        num_sections, = struct.unpack('<I', f.read(4))
        for i in range(num_sections):
            section_type, section_len = struct.unpack('<2I', f.read(8))
            decode_soft_section[section_type](io_range(f, section_len - 8))

        assert(not f.read())

class G1MGSection(object):
    def __init__(self, f, g1m, g1mg):
        self.orig_val = f.getvalue()
        self.g1mg = g1mg
        self.g1m = g1m

    def getvalue(self):
        return self.orig_val

class G1MGBoneMap(G1MGSection):
    def __init__(self, f, g1m, g1mg):
        G1MGSection.__init__(self, f, g1m, g1mg)
        num_maps, = struct.unpack('<I', f.read(4))
        pr_verbose('Num bone maps:', num_maps)
        dtype = numpy.dtype([
            ('id', numpy.uint32, 1), # I think this is a unique ID for the bone ->
                                     # vg mapping. Each unique mapping in the file
                                     # gets an index starting at 0 and
                                     # incrementing by 1 each time. If a mapping
                                     # is repeated from an earlier sub-mesh it
                                     # will have the same ID.
            ('zero', numpy.uint32, 1),
            ('bone', numpy.uint32, 1),
        ])
        g1mg.bone_maps = collections.OrderedDict()
        g1m.import_oid()
        for i in range(num_maps):
            num_maps, = struct.unpack('<I', f.read(4))
            data = numpy.frombuffer(f.read(num_maps * 4 * 3), dtype)
            pr_verbose('Map %i, len %i:' % (i, len(data)))
            vgmap = collections.OrderedDict()
            for vg,d in enumerate(data):
                try:
                    bone_name = g1m.oid_map[list(g1m.chunks[b'G1MS'].indices).index(d['bone'])]
                except:
                    bone_name = 'UnnamedBone#%d' % d['bone']
                pr_verbose(
                        '  VG:', vg*3,
                        'BoneID:', d['bone'], repr(bone_name),
                        'MapID:', d['id'],
                        'Unknown:', d['zero'],
                )
                vgmap[bone_name] = vg*3
            g1mg.bone_maps[i] = vgmap
            pr_verbose()

        assert(not f.read())

    def getvalue(self):
        f = io.BytesIO()
        f.write(struct.pack('<I', len(self.g1mg.bone_maps)))
        self.g1m.import_oid()
        reverse_oid_map = self.g1m.oid_map.reverse()
        bone_map_ids = {}
        for vgmap in self.g1mg.bone_maps.values():
            f.write(struct.pack('<I', len(vgmap)))
            for i, (bone_name, vg) in enumerate(vgmap.items()):
                assert(i*3 == vg)
                if bone_name.startswith('UnnamedBone#'):
                    bone_id = int(bone_name.partition('#')[2])
                else:
                    bone_id = self.g1m.chunks[b'G1MS'].indices[reverse_oid_map[bone_name]]
                map_id = bone_map_ids.setdefault(bone_id, len(bone_map_ids))
                f.write(struct.pack('<3I', map_id, 0, bone_id))

        return f.getvalue()

class G1MGSurfaceMap(G1MGSection):
    def __init__(self, f, g1m, g1mg):
        G1MGSection.__init__(self, f, g1m, g1mg)

        SurfaceMap = numpy.dtype([
            ('u0', numpy.uint32, 2),
            ('bone_map', numpy.uint32, 1),
            ('u1', numpy.uint32, 11),
        ])

        num_maps, = struct.unpack('<I', f.read(4))

        g1mg.surface_maps = numpy.frombuffer(f.read(SurfaceMap.itemsize * num_maps), SurfaceMap)
        pr_verbose('Surfaces:\n', g1mg.surface_maps)
        pr_verbose()

        assert(not f.read())

    def getvalue(self):
        surface_maps = self.g1mg.surface_maps
        return struct.pack('<I', len(surface_maps)) + surface_maps.tobytes()

class OIDMap(dict):
    def __init__(self, f):
        for l in f:
            if l.startswith(';'):
                continue
            id, _, name = l.rstrip().partition(',')
            if id and name:
                self[int(id)] = name

    def reverse(self):
        return dict(map(reversed, self.items()))

def align(file, alignment):
    off = file.tell()
    mod = off % alignment
    if mod == 0:
        return
    file.seek(alignment - mod, 1)

class G1MFChunk(G1MChunk):
    dtype = numpy.dtype([
        ('u0', numpy.uint32, 13),
        ('num_bone_maps', numpy.uint32, 1),
        ('num_individual_bone_maps', numpy.uint32, 1),
        ('u1', numpy.uint32, 58),
    ])

    def __init__(self, f, version, g1m):
        assert(version == b'9200')
        G1MChunk.__init__(self, f, version, g1m)
        self.data, = numpy.frombuffer(f.read(self.dtype.itemsize), self.dtype)
        pr_verbose(self.data)

        assert(not f.read())

    def getvalue(self):
        f = io.BytesIO()
        f.write(self.data['u0'].tobytes())
        f.write(struct.pack('<I', len(self.g1m.chunks[b'G1MG'].bone_maps)))
        f.write(struct.pack('<I', sum(map(len,self.g1m.chunks[b'G1MG'].bone_maps.values()))))
        f.write(self.data['u1'].tobytes())
        return f.getvalue()

class G1MSChunk(G1MChunk):
    def __init__(self, f, version, g1m):
        assert(version == b'2300')
        G1MChunk.__init__(self, f, version, g1m)
        header = struct.unpack('<2I4H', f.read(16))
        pr_verbose(header)
        (bones_offset, unk_10, num_bones, num_indices, num_parents, unk_1A) = header

        self.indices = numpy.frombuffer(f.read(num_indices * 2), numpy.int16)
        pr_verbose(self.indices)
        self.parents = numpy.frombuffer(f.read(num_parents * 2), numpy.int16)
        pr_verbose(self.parents)

        align(f, 4)
        assert(f.tell() == bones_offset-12)
        self.bones_raw = f.read()
        #print_unknown('Bones:', self.bones_raw)

class G1MGChunk(G1MChunk):
    decode_g1mg_section = {
            # 0x10001: dump_unknown_section,
            0x10006: G1MGBoneMap,
            0x10008: G1MGSurfaceMap,
            # 0x10009: dump_unknown_section,
    }

    def __init__(self, f, version, g1m):
        assert(version == b'4400')
        G1MChunk.__init__(self, f, version, g1m)
        self.header = struct.unpack('<4sI6fI', f.read(36))
        pr_verbose(self.header)
        (platform, unk_10, min_x, min_y, min_z, max_x, max_y, max_z, num_sections) = self.header
        assert(platform == b'DX11')
        self.chunks = collections.OrderedDict()
        for i in range(num_sections):
            section_type, section_len = struct.unpack('<2I', f.read(8))
            pr_verbose(hex(section_type))
            buf = io_range(f, section_len - 8)
            if section_type in self.decode_g1mg_section:
                self.chunks[section_type] = \
                    self.decode_g1mg_section[section_type](buf, g1m, self)
            else:
                self.chunks[section_type] = G1MGSection(buf, g1m, self)

    def getvalue(self):
        f = io.BytesIO()
        f.write(struct.pack('<4sI6fI', *self.header))
        for section_id, chunk in self.chunks.items():
            buf = chunk.getvalue()
            f.write(struct.pack('<2I', section_id, len(buf) + 8))
            f.write(buf)
        return f.getvalue()

class G1MFile(object):
    chunk_decoders = {
        b'SOFT': SOFTChunk,
        b'G1MS': G1MSChunk,
        b'G1MG': G1MGChunk,
        b'G1MF': G1MFChunk,
        #b'G1MF': DumpUnknownG1MChunk,
    }

    G1MHeader = numpy.dtype([
        ('signature', numpy.character, 4),
        ('version', numpy.character, 4),
        ('file_size', numpy.uint32, 1),
        ('header_size', numpy.uint32, 1),
        ('u10', numpy.uint32, 1),
        ('num_chunks', numpy.uint32, 1),
    ])

    def __init__(self, f, decode_chunks):
        self.name = f.name
        self.oid_map = None
        self.header, = numpy.frombuffer(f.read(24), self.G1MHeader)
        pr_verbose(self.header)
        (eyecatcher, version, file_size, header_size, u10, chunks) = self.header
        assert(bytes(reversed(eyecatcher)) == b'G1M_')
        assert(version == b'7300')

        f.seek(header_size)
        self.chunks = collections.OrderedDict()
        for i in range(chunks):
            eyecatcher, chunk_version, chunk_size = struct.unpack('<4s4sI', f.read(12))
            eyecatcher = bytes(reversed(eyecatcher))
            pr_verbose(eyecatcher, chunk_version)
            buf = io_range(f, chunk_size - 12)
            if eyecatcher in self.chunk_decoders and (not decode_chunks or eyecatcher in decode_chunks):
                self.chunks[eyecatcher] = \
                    self.chunk_decoders[eyecatcher](buf, chunk_version, self)
            else:
                self.chunks[eyecatcher] = G1MChunk(buf, chunk_version, self)

    def write(self, f):
        f.write(self.header.tobytes())

        for eyecatcher, chunk in self.chunks.items():
            buf = chunk.getvalue()
            f.write(struct.pack('<4s4sI', bytes(reversed(eyecatcher)), chunk.version, len(buf) + 12))
            f.write(buf)

        file_size = f.tell()
        f.seek(8)
        f.write(struct.pack('<I', file_size))

    def import_oid(self):
        if self.oid_map is not None:
            return

        try:
            oidfilename,ext = os.path.splitext(self.name)
            while ext and ext.lower() != '.g1m':
                oidfilename,ext = os.path.splitext(oidfilename)
            oidf = open(oidfilename + '.oid', 'r')
        except OSError as e:
            print('Cannot open %s: %s' % (oidfilename, str(e)))
        else:
            self.oid_map = OIDMap(oidf)
            print('Loaded Object ID map')
            #pr_verbose(self.oid_map)

    def export_vgmaps(self, print=print):
        G1MG = self.chunks[b'G1MG']
        dir = os.path.splitext(self.name)[0]
        print('Exporting %i vertex group maps' % len(G1MG.surface_maps))
        for i, surface_map in enumerate(G1MG.surface_maps):
            vgmap = G1MG.bone_maps[surface_map['bone_map']]
            path = os.path.join(dir, '%d.vgmap' % i)
            try:
                json.dump(vgmap, open(path, 'w'), indent=2)
            except Exception as e:
                print('Unable to dump vertex group mapping:', str(e))
            else:
                print('Exported', path)

    def import_vgmaps(self, print=print):
        G1MG = self.chunks[b'G1MG']
        dir = os.path.splitext(self.name)[0]
        # Remove write protection:
        G1MG.surface_maps = G1MG.surface_maps.copy()
        for filename in glob.glob(os.path.join(dir, '*.vgmap')):
            basename, ext = os.path.splitext(os.path.basename(filename))
            if not basename.isdecimal():
                continue
            surface = int(basename)
            if surface >= len(G1MG.surface_maps):
                print('%s is out of range' % filename)
                continue
            vgmap = json.load(open(filename, 'r'))

            # Resulted in crashes:
            bone_map_idx = surface

            G1MG.surface_maps[surface]['bone_map'] = bone_map_idx
            G1MG.bone_maps[bone_map_idx] = vgmap
            print('Imported %s as bone map %i...' % (filename, bone_map_idx))

def parse_args():
    global verbosity

    parser = argparse.ArgumentParser(description = 'DOA6 g1m Tool')
    parser.add_argument('files', nargs='*',
            help='List of g1m files to parse')
    parser.add_argument('--export-vgmap', action='store_true',
            help='Extract vertex group maps from g1m file')
    parser.add_argument('--import-vgmap', action='store_true',
            help='Import vertex group maps to g1m file')
    parser.add_argument('--test', action='store_true',
            help='Verify importing & exporting a g1m file')
    parser.add_argument('--verbose', '-v', action='count', default=0,
            help='Level of verbosity')
    args = parser.parse_args()

    sections = set()
    if args.export_vgmap:
        sections = sections.union({b'G1MS', b'G1MG'})
    if args.import_vgmap:
        sections = sections.union({b'G1MS', b'G1MG', b'G1MF'})
    verbosity = args.verbose
    if not verbosity and not sections and not args.test:
        verbosity = 1

    return (args, sections)

def main_standalone():
    args, sections=  parse_args()
    for arg in args.files:
        print('Parsing %s...' % arg)
        g1m = G1MFile(open(arg, 'rb'), sections)

        if args.test:
            buf = io.BytesIO()
            g1m.write(buf)
            print('Writing %s...' % (arg + '.TEST'))
            open(arg + '.TEST', 'wb').write(buf.getvalue())
            assert(open(arg, 'rb').read() == buf.getvalue())
            print('Test #1 succeeded')

        if args.import_vgmap:
            g1m.import_vgmaps()
            if not os.path.exists(arg + '.bak'):
                try:
                    os.rename(arg, arg + '.bak')
                except OSError:
                    pass
            print('Writing %s...' % arg)
            g1m.write(open(arg, 'wb'))

        if args.test:
            buf = io.BytesIO()
            g1m.write(buf)
            buf.name = arg
            buf.seek(0)
            G1MFile(buf, None)
            print('Test #2 succeeded')

        if args.export_vgmap:
            g1m.export_vgmaps()

if 'bpy' in globals():
    class ImportDOA6Soft(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
        """Import DOA6 Soft Body nodes"""
        bl_idname = "import_mesh.doa6_soft"
        bl_label = "Import DOA6 Soft Body nodes"
        bl_options = {'UNDO'}

        filename_ext = '.g1m'
        filter_glob = bpy.props.StringProperty(
                default='*.g1m',
                options={'HIDDEN'},
                )

        def execute(self, context):
            G1MFile(open(self.filepath, 'rb'), {b'SOFT'})
            return {'FINISHED'}

    class UpdateDOA6Soft(bpy.types.Operator):
        """Update DOA6 soft body vertex positions"""
        bl_idname = "mesh.update_doa6_soft_body"
        bl_label = "Update DOA6 soft body vertex positions"
        bl_options = {'UNDO'}

        WeightedNode = collections.namedtuple('WeightedNode', ['pos', 'weights'])

        def find_targets(self, context):
            grid = None
            targets = []
            for obj in context.selected_objects:
                if obj.name.find('.SOFT[') != -1:
                    while obj.parent and obj.parent.name.find('.SOFT['):
                        obj = obj.parent
                    if grid and grid != obj:
                        raise Fatal('Multiple soft body grids selected')
                    grid = obj
                else:
                    if set(['TEXCOORD%u.%s'%(x,y) for x in (8, 9) for y in ('xy', 'zw')]).difference(obj.data.uv_layers.keys()):
                        raise Fatal('Selected object does not have expected TEXCOORD8+9 UV layers')
                    if set(['%s.%s'%(x,y) for x in ('PSIZE', 'FOG') for y in 'xyzw']).difference(obj.data.vertex_layers_int.keys()):
                        raise Fatal('Selected object does not have expected PSIZE & FOG integer vertex layers')
                    if 'SAMPLE.x' not in obj.data.vertex_layers_float.keys():
                        raise Fatal('Selected object does not have expected SAMPLE float vertex layer')
                    targets.append(obj)
            if not grid:
                raise Fatal('No soft body grids selected')
            if not targets:
                raise Fatal('No target meshes selected')
            return (grid, targets)

        def find_parallel_sides(self, nodes, n):
            # We need to find sides pointing in the same direction. We don't
            # necessarily know what order the nodes are in (though maybe with
            # some analysis of how the nodes are typically layed out we could
            # assume something?), so we will arbitrarily take a vector
            # connecting the first two corners then scan through all
            # permutations of pairs of the remaining corners to locate the
            # three sides that most closely match that vector.
            #
            # Assumes all the sides we are looking for have approximately the
            # same length and direction.
            #
            side1_vec = nodes[1].pos - nodes[0].pos
            other_pairs = itertools.permutations(nodes[2:], 2)
            other_vecs = [(numpy.linalg.norm(y.pos - x.pos - side1_vec), x,y) for x,y in other_pairs]
            other_vecs = sorted(other_vecs, key=lambda x: x[0])[:n-1]
            other_vecs = list(zip(*list(zip(*other_vecs))[1:]))
            return [(nodes[0], nodes[1])] + other_vecs

        @staticmethod
        def angle_between(p1, corner, p2):
            v0 = numpy.array(p1) - numpy.array(corner)
            v1 = numpy.array(p2) - numpy.array(corner)
            return math.atan2(numpy.linalg.norm(numpy.cross(v0, v1)), numpy.dot(v0, v1))

        @classmethod
        def ratio_along_line(cls, pos, line_pos_1, line_pos_2):
            # Finds how far along a line a given point lies, returning 0.0 at
            # line_pos_1, and 1.0 at line_pos_2, and whatever between them.
            # This point does not need to lie on the line, but the closest
            # point on the line will be considered.
            angle = cls.angle_between(pos, line_pos_1, line_pos_2)
            dist_p1_to_closest = numpy.linalg.norm(numpy.array(pos) - numpy.array(line_pos_1)) * math.cos(angle)
            return dist_p1_to_closest / numpy.linalg.norm(line_pos_2 - line_pos_1)

        @staticmethod
        def interpolate_linear(n1, n2, ratio):
            return (1.0-ratio)*n1 + ratio*n2

        @classmethod
        def interpolate_weighted_nodes(cls, n1, n2, ratio):
            pos = cls.interpolate_linear(n1.pos, n2.pos, ratio)
            weights = [cls.interpolate_linear(x,y,ratio) for (x,y) in zip(n1.weights, n2.weights)]
            return cls.WeightedNode(pos, weights)

        def interpolate_weights_linear(self, pos, nodes):
            if len(nodes) != 2:
                self.report({'WARNING'}, 'Vertex at %s surrounded by irregular number of %u nodes' % (pos, len(nodes)))
                return None
            r = self.ratio_along_line(pos, nodes[0].pos, nodes[1].pos)
            interpolated = self.interpolate_weighted_nodes(nodes[0], nodes[1], r)
            return interpolated.weights

        def interpolate_weights_bilinear(self, pos, nodes):
            if len(nodes) != 4:
                return self.interpolate_weights_linear(pos, nodes)
            sides = self.find_parallel_sides(nodes, 2)
            interpolated_line = []
            for n1,n2 in sides:
                r = self.ratio_along_line(pos, n1.pos, n2.pos)
                interpolated = self.interpolate_weighted_nodes(n1, n2, r)
                interpolated_line.append(interpolated)
            return self.interpolate_weights_linear(pos, interpolated_line)

        def interpolate_weights_trilinear(self, pos, nodes):
            if len(nodes) != 8:
                return self.interpolate_weights_bilinear(pos, nodes)
            # The nodes should form a cube or rectangular prism, and we want to
            # interpolate on four sides pointing in one direction to form a
            # square, then on two opposite sides of that square to form a line,
            # then on that line to find a point that should match the vertex
            # position. If we also interpolate weights between the corners,
            # where each corner has its own weight set at 1.0 and all other
            # weights set at 0.0 than then interpolated weights should be
            # usable to reconstruct the vertex location given the corner
            # positions.
            sides = self.find_parallel_sides(nodes, 4)
            interpolated_square = []
            for n1,n2 in sides:
                # Can probably get away with calculating r once and reusing it
                # for the next three sides, but do it each time allowing for
                # the nodes to not quite form a grid:
                r = self.ratio_along_line(pos, n1.pos, n2.pos)
                interpolated = self.interpolate_weighted_nodes(n1, n2, r)
                interpolated_square.append(interpolated)
            return self.interpolate_weights_bilinear(pos, interpolated_square)

        def update_soft_body_sim(self, grid_parent, target):
            node_locations = numpy.array([ x.location for x in grid_parent.children ])
            node_ids = [ int(x.name.rpartition('[')[2].rstrip(']')) for x in grid_parent.children ]
            #print('Nodes', list(zip(node_ids, node_locations)))

            uv_layer_names = ['TEXCOORD%u.%s'%(x,y) for x in (8, 9) for y in ('xy', 'zw')]
            node_layer_names = ['%s.%s'%(x,y) for x in ('PSIZE', 'FOG') for y in 'xyzw']

            for layer in uv_layer_names:
                try:
                    target['3DMigoto:' + layer]['flip_v'] = False
                except:
                    target['3DMigoto:' + layer] = {'flip_v': False}

            Nodes = collections.namedtuple('Node', ['id', 'dist', 'pos', 'vec'])

            max_errors = [(0.0, None, None, [])]*9
            for l in target.data.loops:
                vertex = target.data.vertices[l.vertex_index]
                vectors = [vertex.co]*len(node_locations) - node_locations

                # numpy.linalg.norm can calculate distance reportedly faster
                # than scipy.spacial.distance.euclidean:
                distances = numpy.linalg.norm(vectors, axis=1)
                sorted_nodes = sorted([Nodes(*x) for x in zip(node_ids, distances, node_locations, vectors)],
                        key=lambda x: x.dist, reverse=True)

                # We need to exclude any nodes in the same direction from this
                # vertex as earlier nodes, so that vertices outside of the grid
                # will only use the nearest four nodes and so that vertices
                # near a node will use the nodes forming a cube around it and
                # not leach over to a neighbouring cube that happens to have a
                # closer node.
                #
                # For each node we are including form a plane intersecting the
                # node with the normal pointing towards this vertex. Nodes that
                # lie on the far side of the plane are excluded. Keep going
                # until we have 8 nodes that should form a cube around the
                # vertex, or have run out of nodes.
                surrounding_nodes = []
                non_adjacent_nodes = []
                while sorted_nodes:
                    node = sorted_nodes.pop()
                    surrounding_nodes.append(node)
                    if len(surrounding_nodes) == 8:
                        non_adjacent_nodes.extend(sorted_nodes)
                        break
                    # To distinguish the two sides of a plane, calculate a
                    # normal n to it at some point p. Then a point v is on the
                    # side where the normal points at if (v−p)⋅n>0 and on the
                    # other side if (v−p)⋅n<0.
                    # - https://math.stackexchange.com/questions/214187/point-on-the-left-or-right-side-of-a-plane-in-3d-space#214194
                    for i, node1 in reversed(list(enumerate(sorted_nodes))):
                        if numpy.dot(node1.pos - node.pos, node.vec) < 0:
                            non_adjacent_nodes.append(sorted_nodes.pop(i))

                num_surrounding_nodes = len(surrounding_nodes)

                # If a vertex falls outside the grid we can try to handle it by
                # finding the nearest cube of nodes and interpolating outside
                # of that cube. For the moment we are only going to attempt
                # this if we have found four surrounding nodes indicating this
                # vertex is on the outside of one of the flat sides of the grid
                # (and not diagonally out from a corner). Find the midpoint of
                # the surrounding nodes and the next nearest four nodes to that
                # point should (hopefully) be the next four points on the cube
                # (if not we could do a cross product of a corner on the square
                # to find the normal than restrict nodes we consider to those
                # that are roughly lined up with one of the corners)
                if num_surrounding_nodes == 4:
                    midpoint = numpy.average([x.pos for x in surrounding_nodes], axis=0)
                    sorted_nodes = sorted(non_adjacent_nodes, key=lambda x: numpy.linalg.norm(x.pos - midpoint))
                    surrounding_nodes.extend(sorted_nodes[:8 - num_surrounding_nodes])

                # Sort by Node ID (probably unnecessary, but puts it in the same
                # order as original for comparison)
                surrounding_nodes = sorted(surrounding_nodes, key=lambda x: x.id)

                weighted_nodes = [self.WeightedNode(n.pos, [0.0]*i + [1.0] + [0.0]*(len(surrounding_nodes)-i-1)) \
                        for i,n in enumerate(surrounding_nodes)]
                weights = self.interpolate_weights_trilinear(vertex.co, weighted_nodes)
                if weights is None:
                    continue

                # Check how accurate our result is - calculate the position
                # based on the node weights and compare it to the vertex
                # position, warning if any vertices are excessively inaccurate.
                pos = numpy.array([0.0,0.0,0.0])
                for i,n in enumerate(weighted_nodes):
                    pos += n.pos * weights[i]
                error = numpy.linalg.norm(pos - vertex.co)
                if error > max_errors[num_surrounding_nodes][0]:
                    max_errors[num_surrounding_nodes] = (vertex.index, error, vertex.co, pos, weights)

                # Zero out existing weights:
                for i in range(4):
                    target.data.uv_layers[uv_layer_names[i]].data[l.index].uv = (0, 0)

                # Write new soft body node IDs and weights to the vertices:
                for i,n in enumerate(surrounding_nodes):
                    target.data.vertex_layers_int[node_layer_names[i]].data[vertex.index].value = n.id
                    target.data.uv_layers[uv_layer_names[i//2]].data[l.index].uv[i%2] = weights[i]

            for i,max_error in enumerate(max_errors):
                if max_error[1] is not None:
                    self.report({'INFO'}, "Maximum error for %i surrounding nodes: vertex %u off by %f, vertex position %s, calculated position %s, weights %s" % ((i,) + max_error))

        def execute(self, context):
            try:
                grid_parent, targets = self.find_targets(context)
                for target in targets:
                    self.update_soft_body_sim(grid_parent, target)
            except Fatal as e:
                self.report({'ERROR'}, str(e))

            return {'FINISHED'}

    class ExtractDOA6VGMaps(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
        """"Extract DOA6 vertex group maps"""
        bl_idname = "misc.extract_doa6_vgmaps"
        bl_label = "Extract DOA6 vertex group maps"
        bl_options = {'UNDO'}

        filename_ext = '.g1m'
        filter_glob = bpy.props.StringProperty(
                default='*.g1m',
                options={'HIDDEN'},
                )

        files = bpy.props.CollectionProperty(
                name="File Path",
                type=bpy.types.OperatorFileListElement,
                )

        def execute(self, context):
            def redirect_print(*args, **kwargs):
                buf = io.StringIO()
                print(*args, file=buf, end='', **kwargs)
                self.report({'INFO'}, buf.getvalue())

            dirname = os.path.dirname(self.filepath)
            for filename in self.files:
                redirect_print('Parsing %s...' % filename.name)
                g1m = G1MFile(open(os.path.join(dirname, filename.name), 'rb'), {b'G1MS', b'G1MG'})
                g1m.export_vgmaps(print=redirect_print)

            return {'FINISHED'}

    def menu_func_import_soft(self, context):
        self.layout.operator(ImportDOA6Soft.bl_idname, text="DOA6 Soft Body (.g1m)")

    def register():
        bpy.utils.register_module(__name__)
        bpy.types.INFO_MT_file_import.append(menu_func_import_soft)

    def unregister():
        bpy.utils.unregister_module(__name__)
        bpy.types.INFO_MT_file_import.remove(menu_func_import_soft)

if __name__ == '__main__':
    if 'bpy' in globals():
        register()
    else:
        main_standalone()
