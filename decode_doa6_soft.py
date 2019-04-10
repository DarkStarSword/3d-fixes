#!/usr/bin/env python3

bl_info = {
    "name": "DOA6 Soft Body",
    "author": "Ian Munsie (darkstarsword@gmail.com)",
    "location": "File > Import-Export",
    "description": "Work with DOA6 soft body meshes",
    "category": "Import-Export",
    "tracker_url": "https://github.com/DarkStarSword/3d-fixes/issues",
}

import os, struct, sys, numpy, io, copy

try:
    import bpy
except ImportError as e:
    print('Running standalone - decoding only, no Blender integration')
else:
    import bpy_extras

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
    if verbosity:
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

def dump_unknown_section(f):
    print_unknown('Unknown section:', f.read())

decode_soft_section = {
    0x80001: decode_soft_node_regions,
    0x80002: dump_unknown_section,
}

def io_range(f, len):
    b = io.BytesIO(f.read(len))
    b.name = f.name
    return b

def decode_soft(f):
    num_sections, = struct.unpack('<I', f.read(4))
    for i in range(num_sections):
        section_type, section_len = struct.unpack('<2I', f.read(8))
        decode_soft_section[section_type](io_range(f, section_len - 8))

    assert(not f.read())

chunk_decoders = {
    b'SOFT': decode_soft,
}

def decode_g1m(f):
    (eyecatcher, version, file_size, header_size, u10, chunks) = struct.unpack('<4s4s4I', f.read(24))
    assert(bytes(reversed(eyecatcher)) == b'G1M_')
    assert(version == b'7300')

    f.seek(header_size)
    for i in range(chunks):
        eyecatcher, chunk_version, chunk_size = struct.unpack('<4s2I', f.read(12))
        eyecatcher = bytes(reversed(eyecatcher))
        #pr_verbose(eyecatcher)
        if eyecatcher in chunk_decoders:
            chunk_decoders[eyecatcher](io_range(f, chunk_size - 12))
        else:
            f.seek(chunk_size - 12, 1)

def main_standalone():
    for arg in sys.argv[1:]:
        print('Parsing %s...' % arg)
        decode_g1m(open(arg, 'rb'))

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
            decode_g1m(open(self.filepath, 'rb'))
            return {'FINISHED'}

    class UpdateDOA6Soft(bpy.types.Operator):
        """Update DOA6 soft body vertex positions"""
        bl_idname = "mesh.update_doa6_soft_body"
        bl_label = "Update DOA6 soft body vertex positions"
        bl_options = {'UNDO'}

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

        def update_soft_body_sim(self, grid_parent, target):
            node_locations = numpy.array([ x.location for x in grid_parent.children ])
            node_ids = [ int(x.name.rpartition('[')[2].rstrip(']')) for x in grid_parent.children ]
            #print('Nodes', list(zip(node_ids, node_locations)))

            uv_layer_names = ['TEXCOORD%u.%s'%(x,y) for x in (8, 9) for y in ('xy', 'zw')]
            node_layer_names = ['%s.%s'%(x,y) for x in ('PSIZE', 'FOG') for y in 'xyzw']

            flip_uv = {}
            for layer in uv_layer_names:
                layer_props = target['3DMigoto:' + layer]
                if isinstance(layer_props, dict) and layer_props['flip_v']:
                    flip_uv[layer] = lambda uv: (uv[0], 1.0 - uv[1])
                else:
                    flip_uv[layer] = lambda uv: uv

            for l in target.data.loops:
                vertex = target.data.vertices[l.vertex_index]
                vectors = [vertex.co]*len(node_locations) - node_locations

                # numpy.linalg.norm can calculate distance reportedly faster
                # than scipy.spacial.distance.euclidean:
                distances = numpy.linalg.norm(vectors, axis=1)
                sorted_nodes = sorted(zip(node_ids, distances, node_locations, vectors), key=lambda x: x[1], reverse=True)

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
                while sorted_nodes:
                    (node, distance, node_location, normal) = sorted_nodes.pop()
                    surrounding_nodes.append((node, distance, node_location))
                    if len(surrounding_nodes) == 8:
                        break
                    # To distinguish the two sides of a plane, calculate a
                    # normal n to it at some point p. Then a point v is on the
                    # side where the normal points at if (v−p)⋅n>0 and on the
                    # other side if (v−p)⋅n<0.
                    # - https://math.stackexchange.com/questions/214187/point-on-the-left-or-right-side-of-a-plane-in-3d-space#214194
                    for i, (node1, distance1, node_location1, normal1) in reversed(list(enumerate(sorted_nodes))):
                        if numpy.dot(node_location1 - node_location, normal) < 0:
                            del sorted_nodes[i]

                diag_dist = numpy.linalg.norm(surrounding_nodes[0][2] - surrounding_nodes[-1][2])
                total_dist = sum([x[1] for x in surrounding_nodes])
                closest = min([x[1] for x in surrounding_nodes])
                furthest = max([x[1] for x in surrounding_nodes])

                # Sort by Node ID (probably unecessary, but puts it in the same
                # order as original for comparison)
                surrounding_nodes = sorted(surrounding_nodes, key=lambda x: x[0])

                # Calculate weights. I'm not positive how these are supposed to
                # be calculated, so this is just an approximation. Both of
                # these options give approximately the same result:
                #weighted_nodes = [(x, closest+furthest-y) for (x,y,_) in surrounding_nodes]
                weighted_nodes = [(x, diag_dist-y) for (x,y,_) in surrounding_nodes]
                fudge = 3.3
                weighted_total = sum([x[1]**fudge for x in weighted_nodes])
                weighted_nodes = [(x, (y**fudge)/(weighted_total)) for (x,y) in weighted_nodes]

                for i in range(4):
                    target.data.uv_layers[uv_layer_names[i]].data[l.index].uv = (0, 0)
                    try:
                        target['3DMigoto:' + uv_layer_names[i]]['flip_v'] = False
                    except:
                        target['3DMigoto:' + uv_layer_names[i]] = {'flip_v': False}
                for i, (node, weight) in enumerate(weighted_nodes):
                    target.data.vertex_layers_int[node_layer_names[i]].data[vertex.index].value = node
                    target.data.uv_layers[uv_layer_names[i//2]].data[l.index].uv[i%2] = weight

                #if (vertex.index == 0 or vertex.index == 27):
                #    print('Total', total_dist, 'Closest', closest, 'Furthest', furthest)
                #    print('Distances', [(x,y) for (x,y,_) in surrounding_nodes])
                #    print('Weighted', weighted_nodes)
                #    orig_nodes = [target.data.vertex_layers_int[layer].data[vertex.index].value \
                #            for layer in node_layer_names
                #    ]
                #    orig_weights = [flip_uv[layer](target.data.uv_layers[layer].data[l.index].uv)[z] \
                #            for layer in uv_layer_names
                #            for z in (0,1)
                #    ]
                #    print('Original', [(x,y) for (x,y) in zip(orig_nodes, orig_weights) if y])
                #    #return

        def execute(self, context):
            try:
                grid_parent, targets = self.find_targets(context)
                for target in targets:
                    self.update_soft_body_sim(grid_parent, target)
            except Fatal as e:
                self.report({'ERROR'}, str(e))

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
        verbosity = 1
        main_standalone()
