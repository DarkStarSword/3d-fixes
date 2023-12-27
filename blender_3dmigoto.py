#!/usr/bin/env python3

# Updated to Blender 2.93
bl_info = {
    "name": "3DMigoto",
    "blender": (2, 93, 0),
    "author": "Ian Munsie (darkstarsword@gmail.com)",
    "location": "File > Import-Export",
    "description": "Imports meshes dumped with 3DMigoto's frame analysis and exports meshes suitable for re-injection",
    "category": "Import-Export",
    "tracker_url": "https://github.com/DarkStarSword/3d-fixes/issues",
}

# TODO:
# - Option to reduce vertices on import to simplify mesh (can be noticeably lossy)
# - Option to untesselate triangles on import?
# - Operator to generate vertex group map
# - Generate bones, using vertex groups to approximate position
#   - And maybe orientation & magnitude, but I'll have to figure out some funky
#     maths to have it follow the mesh like a cylinder
# - Test in a wider variety of games
# - Handle TANGENT better on both import & export?

import io
import re
from array import array
import struct
import numpy
import itertools
import collections
import os
from glob import glob
import json
import copy
import textwrap

import bpy
from bpy_extras.io_utils import unpack_list, ImportHelper, ExportHelper, axis_conversion
from bpy.props import BoolProperty, StringProperty, CollectionProperty
from bpy_extras.image_utils import load_image
from mathutils import Matrix, Vector
try:
    from bl_ui.generic_ui_list import draw_ui_list
except ImportError:
    # Blender older than 3.5. Just disable the semantic remap feature
    draw_ui_list = None

############## Begin (deprecated) Blender 2.7/2.8 compatibility wrappers (2.7 options removed) ##############

from bpy_extras.io_utils import orientation_helper
IOOBJOrientationHelper = type('DummyIOOBJOrientationHelper', (object,), {})

import_menu = bpy.types.TOPBAR_MT_file_import
export_menu = bpy.types.TOPBAR_MT_file_export
vertex_color_layer_channels = 4

# https://theduckcow.com/2019/update-addons-both-blender-28-and-27-support/
def make_annotations(cls):
    """Converts class fields to annotations"""
    bl_props = {k: v for k, v in cls.__dict__.items() if isinstance(v, tuple)}
    if bl_props:
        if '__annotations__' not in cls.__dict__:
            setattr(cls, '__annotations__', {})
        annotations = cls.__dict__['__annotations__']
        for k, v in bl_props.items():
            annotations[k] = v
            delattr(cls, k)
    return cls

def select_get(object):
    return object.select_get()

def select_set(object, state):
    object.select_set(state)

def hide_get(object):
    return object.hide_get()

def hide_set(object, state):
    object.hide_set(state)

def set_active_object(context, obj):
    context.view_layer.objects.active = obj # the 2.8 way

def get_active_object(context):
    return context.view_layer.objects.active

def link_object_to_scene(context, obj):
    context.scene.collection.objects.link(obj)

def unlink_object(context, obj):
    context.scene.collection.objects.unlink(obj)

def matmul(a, b):
    import operator # to get function names for operators like @, +, -
    return operator.matmul(a, b) # the same as writing a @ b

############## End (deprecated) Blender 2.7/2.8 compatibility wrappers (2.7 options removed) ##############


supported_topologies = ('trianglelist', 'pointlist', 'trianglestrip')

def keys_to_ints(d):
    return {k.isdecimal() and int(k) or k:v for k,v in d.items()}
def keys_to_strings(d):
    return {str(k):v for k,v in d.items()}

class Fatal(Exception): pass

ImportPaths = collections.namedtuple('ImportPaths', ('vb_paths', 'ib_paths', 'use_bin', 'pose_path'))

# TODO: Support more DXGI formats:
f32_pattern = re.compile(r'''(?:DXGI_FORMAT_)?(?:[RGBAD]32)+_FLOAT''')
f16_pattern = re.compile(r'''(?:DXGI_FORMAT_)?(?:[RGBAD]16)+_FLOAT''')
u32_pattern = re.compile(r'''(?:DXGI_FORMAT_)?(?:[RGBAD]32)+_UINT''')
u16_pattern = re.compile(r'''(?:DXGI_FORMAT_)?(?:[RGBAD]16)+_UINT''')
u8_pattern = re.compile(r'''(?:DXGI_FORMAT_)?(?:[RGBAD]8)+_UINT''')
s32_pattern = re.compile(r'''(?:DXGI_FORMAT_)?(?:[RGBAD]32)+_SINT''')
s16_pattern = re.compile(r'''(?:DXGI_FORMAT_)?(?:[RGBAD]16)+_SINT''')
s8_pattern = re.compile(r'''(?:DXGI_FORMAT_)?(?:[RGBAD]8)+_SINT''')
unorm16_pattern = re.compile(r'''(?:DXGI_FORMAT_)?(?:[RGBAD]16)+_UNORM''')
unorm8_pattern = re.compile(r'''(?:DXGI_FORMAT_)?(?:[RGBAD]8)+_UNORM''')
snorm16_pattern = re.compile(r'''(?:DXGI_FORMAT_)?(?:[RGBAD]16)+_SNORM''')
snorm8_pattern = re.compile(r'''(?:DXGI_FORMAT_)?(?:[RGBAD]8)+_SNORM''')

misc_float_pattern = re.compile(r'''(?:DXGI_FORMAT_)?(?:[RGBAD][0-9]+)+_(?:FLOAT|UNORM|SNORM)''')
misc_int_pattern = re.compile(r'''(?:DXGI_FORMAT_)?(?:[RGBAD][0-9]+)+_[SU]INT''')

def EncoderDecoder(fmt):
    if f32_pattern.match(fmt):
        return (lambda data: b''.join(struct.pack('<f', x) for x in data),
                lambda data: numpy.frombuffer(data, numpy.float32).tolist())
    if f16_pattern.match(fmt):
        return (lambda data: numpy.fromiter(data, numpy.float16).tobytes(),
                lambda data: numpy.frombuffer(data, numpy.float16).tolist())
    if u32_pattern.match(fmt):
        return (lambda data: numpy.fromiter(data, numpy.uint32).tobytes(),
                lambda data: numpy.frombuffer(data, numpy.uint32).tolist())
    if u16_pattern.match(fmt):
        return (lambda data: numpy.fromiter(data, numpy.uint16).tobytes(),
                lambda data: numpy.frombuffer(data, numpy.uint16).tolist())
    if u8_pattern.match(fmt):
        return (lambda data: numpy.fromiter(data, numpy.uint8).tobytes(),
                lambda data: numpy.frombuffer(data, numpy.uint8).tolist())
    if s32_pattern.match(fmt):
        return (lambda data: numpy.fromiter(data, numpy.int32).tobytes(),
                lambda data: numpy.frombuffer(data, numpy.int32).tolist())
    if s16_pattern.match(fmt):
        return (lambda data: numpy.fromiter(data, numpy.int16).tobytes(),
                lambda data: numpy.frombuffer(data, numpy.int16).tolist())
    if s8_pattern.match(fmt):
        return (lambda data: numpy.fromiter(data, numpy.int8).tobytes(),
                lambda data: numpy.frombuffer(data, numpy.int8).tolist())

    if unorm16_pattern.match(fmt):
        return (lambda data: numpy.around((numpy.fromiter(data, numpy.float32) * 65535.0)).astype(numpy.uint16).tobytes(),
                lambda data: (numpy.frombuffer(data, numpy.uint16) / 65535.0).tolist())
    if unorm8_pattern.match(fmt):
        return (lambda data: numpy.around((numpy.fromiter(data, numpy.float32) * 255.0)).astype(numpy.uint8).tobytes(),
                lambda data: (numpy.frombuffer(data, numpy.uint8) / 255.0).tolist())
    if snorm16_pattern.match(fmt):
        return (lambda data: numpy.around((numpy.fromiter(data, numpy.float32) * 32767.0)).astype(numpy.int16).tobytes(),
                lambda data: (numpy.frombuffer(data, numpy.int16) / 32767.0).tolist())
    if snorm8_pattern.match(fmt):
        return (lambda data: numpy.around((numpy.fromiter(data, numpy.float32) * 127.0)).astype(numpy.int8).tobytes(),
                lambda data: (numpy.frombuffer(data, numpy.int8) / 127.0).tolist())

    raise Fatal('File uses an unsupported DXGI Format: %s' % fmt)

components_pattern = re.compile(r'''(?<![0-9])[0-9]+(?![0-9])''')
def format_components(fmt):
    return len(components_pattern.findall(fmt))

def format_size(fmt):
    matches = components_pattern.findall(fmt)
    return sum(map(int, matches)) // 8

class InputLayoutElement(object):
    def __init__(self, arg):
        self.RemappedSemanticName = None
        self.RemappedSemanticIndex = None
        if isinstance(arg, io.IOBase):
            self.from_file(arg)
        else:
            self.from_dict(arg)

        self.encoder, self.decoder = EncoderDecoder(self.Format)

    def from_file(self, f):
        self.SemanticName = self.next_validate(f, 'SemanticName')
        self.SemanticIndex = int(self.next_validate(f, 'SemanticIndex'))
        (self.RemappedSemanticName, line) = self.next_optional(f, 'RemappedSemanticName')
        if line is None:
            self.RemappedSemanticIndex = int(self.next_validate(f, 'RemappedSemanticIndex'))
        self.Format = self.next_validate(f, 'Format', line)
        self.InputSlot = int(self.next_validate(f, 'InputSlot'))
        self.AlignedByteOffset = self.next_validate(f, 'AlignedByteOffset')
        if self.AlignedByteOffset == 'append':
            raise Fatal('Input layouts using "AlignedByteOffset=append" are not yet supported')
        self.AlignedByteOffset = int(self.AlignedByteOffset)
        self.InputSlotClass = self.next_validate(f, 'InputSlotClass')
        self.InstanceDataStepRate = int(self.next_validate(f, 'InstanceDataStepRate'))

    def to_dict(self):
        d = {}
        d['SemanticName'] = self.SemanticName
        d['SemanticIndex'] = self.SemanticIndex
        if self.RemappedSemanticName is not None:
            d['RemappedSemanticName'] = self.RemappedSemanticName
            d['RemappedSemanticIndex'] = self.RemappedSemanticIndex
        d['Format'] = self.Format
        d['InputSlot'] = self.InputSlot
        d['AlignedByteOffset'] = self.AlignedByteOffset
        d['InputSlotClass'] = self.InputSlotClass
        d['InstanceDataStepRate'] = self.InstanceDataStepRate
        return d

    def to_string(self, indent=2):
        ret = textwrap.dedent('''
            SemanticName: %s
            SemanticIndex: %i
        ''').lstrip() % (
            self.SemanticName,
            self.SemanticIndex,
        )
        if self.RemappedSemanticName is not None:
            ret += textwrap.dedent('''
                RemappedSemanticName: %s
                RemappedSemanticIndex: %i
            ''').lstrip() % (
                self.RemappedSemanticName,
                self.RemappedSemanticIndex,
            )
        ret += textwrap.dedent('''
            Format: %s
            InputSlot: %i
            AlignedByteOffset: %i
            InputSlotClass: %s
            InstanceDataStepRate: %i
        ''').lstrip() % (
            self.Format,
            self.InputSlot,
            self.AlignedByteOffset,
            self.InputSlotClass,
            self.InstanceDataStepRate,
        )
        return textwrap.indent(ret, ' '*indent)

    def from_dict(self, d):
        self.SemanticName = d['SemanticName']
        self.SemanticIndex = d['SemanticIndex']
        try:
            self.RemappedSemanticName = d['RemappedSemanticName']
            self.RemappedSemanticIndex = d['RemappedSemanticIndex']
        except KeyError: pass
        self.Format = d['Format']
        self.InputSlot = d['InputSlot']
        self.AlignedByteOffset = d['AlignedByteOffset']
        self.InputSlotClass = d['InputSlotClass']
        self.InstanceDataStepRate = d['InstanceDataStepRate']

    @staticmethod
    def next_validate(f, field, line=None):
        if line is None:
            line = next(f).strip()
        assert(line.startswith(field + ': '))
        return line[len(field) + 2:]

    @staticmethod
    def next_optional(f, field, line=None):
        if line is None:
            line = next(f).strip()
        if line.startswith(field + ': '):
            return (line[len(field) + 2:], None)
        return (None, line)

    @property
    def name(self):
        if self.SemanticIndex:
            return '%s%i' % (self.SemanticName, self.SemanticIndex)
        return self.SemanticName

    @property
    def remapped_name(self):
        if self.RemappedSemanticName is None:
            return self.name
        if self.RemappedSemanticIndex:
            return '%s%i' % (self.RemappedSemanticName, self.RemappedSemanticIndex)
        return self.RemappedSemanticName

    def pad(self, data, val):
        padding = format_components(self.Format) - len(data)
        assert(padding >= 0)
        return data + [val]*padding

    def clip(self, data):
        return data[:format_components(self.Format)]

    def size(self):
        return format_size(self.Format)

    def is_float(self):
        return misc_float_pattern.match(self.Format)

    def is_int(self):
        return misc_int_pattern.match(self.Format)

    def encode(self, data):
        # print(self.Format, data)
        return self.encoder(data)

    def decode(self, data):
        return self.decoder(data)

    def __eq__(self, other):
        return \
            self.SemanticName == other.SemanticName and \
            self.SemanticIndex == other.SemanticIndex and \
            self.Format == other.Format and \
            self.InputSlot == other.InputSlot and \
            self.AlignedByteOffset == other.AlignedByteOffset and \
            self.InputSlotClass == other.InputSlotClass and \
            self.InstanceDataStepRate == other.InstanceDataStepRate

class InputLayout(object):
    def __init__(self, custom_prop=[]):
        self.semantic_translations_cache = None
        self.elems = collections.OrderedDict()
        for item in custom_prop:
            elem = InputLayoutElement(item)
            self.elems[elem.name] = elem

    def serialise(self):
        return [x.to_dict() for x in self.elems.values()]

    def to_string(self):
        ret = ''
        for i, elem in enumerate(self.elems.values()):
            ret += 'element[%i]:\n' % i
            ret += elem.to_string()
        return ret

    def parse_element(self, f):
        elem = InputLayoutElement(f)
        self.elems[elem.name] = elem

    def __iter__(self):
        return iter(self.elems.values())

    def __getitem__(self, semantic):
        return self.elems[semantic]

    def untranslate_semantic(self, translated_semantic_name, translated_semantic_index=0):
        semantic_translations = self.get_semantic_remap()
        reverse_semantic_translations = {v: k for k,v in semantic_translations.items()}
        semantic = reverse_semantic_translations[(translated_semantic_name, translated_semantic_index)]
        return self[semantic]

    def encode(self, vertex, vbuf_idx, stride):
        buf = bytearray(stride)

        for semantic, data in vertex.items():
            if semantic.startswith('~'):
                continue
            elem = self.elems[semantic]
            if vbuf_idx.isnumeric() and elem.InputSlot != int(vbuf_idx):
                # Belongs to a different vertex buffer
                continue
            data = elem.encode(data)
            buf[elem.AlignedByteOffset:elem.AlignedByteOffset + len(data)] = data

        assert(len(buf) == stride)
        return buf

    def decode(self, buf, vbuf_idx):
        vertex = {}
        for elem in self.elems.values():
            if elem.InputSlot != vbuf_idx:
                # Belongs to a different vertex buffer
                continue
            data = buf[elem.AlignedByteOffset:elem.AlignedByteOffset + elem.size()]
            vertex[elem.name] = elem.decode(data)
        return vertex

    def __eq__(self, other):
        return self.elems == other.elems

    def apply_semantic_remap(self, operator):
        semantic_translations = {}
        semantic_highest_indices = {}

        for elem in self.elems.values():
            semantic_highest_indices[elem.SemanticName.upper()] = max(semantic_highest_indices.get(elem.SemanticName.upper(), 0), elem.SemanticIndex)

        def find_free_elem_index(semantic):
            idx = semantic_highest_indices.get(semantic, -1) + 1
            semantic_highest_indices[semantic] = idx
            return idx

        for remap in operator.properties.semantic_remap:
            if remap.semantic_to == 'None':
                continue
            if remap.semantic_from in semantic_translations:
                operator.report({'ERROR'}, 'semantic remap for {} specified multiple times, only the first will be used'.format(remap.semantic_from))
                continue
            if remap.semantic_from not in self.elems:
                operator.report({'WARNING'}, 'semantic "{}" not found in imported file, double check your semantic remaps'.format(remap.semantic_from))
                continue

            remapped_semantic_idx = find_free_elem_index(remap.semantic_to)

            operator.report({'INFO'}, 'Remapping semantic {} -> {}{}'.format(remap.semantic_from, remap.semantic_to,
                remapped_semantic_idx or ''))

            self.elems[remap.semantic_from].RemappedSemanticName = remap.semantic_to
            self.elems[remap.semantic_from].RemappedSemanticIndex = remapped_semantic_idx
            semantic_translations[remap.semantic_from] = (remap.semantic_to, remapped_semantic_idx)

        self.semantic_translations_cache = semantic_translations
        return semantic_translations

    def get_semantic_remap(self):
        if self.semantic_translations_cache:
            return self.semantic_translations_cache
        semantic_translations = {}
        for elem in self.elems.values():
            if elem.RemappedSemanticName is not None:
                semantic_translations[elem.name] = \
                    (elem.RemappedSemanticName, elem.RemappedSemanticIndex)
        self.semantic_translations_cache = semantic_translations
        return semantic_translations

class HashableVertex(dict):
    def __hash__(self):
        # Convert keys and values into immutable types that can be hashed
        immutable = tuple((k, tuple(v)) for k,v in sorted(self.items()))
        return hash(immutable)

class IndividualVertexBuffer(object):
    '''
    One individual vertex buffer. Multiple vertex buffers may contain
    individual semantics which when combined together make up a vertex buffer
    group.
    '''

    vb_elem_pattern = re.compile(r'''vb\d+\[\d*\]\+\d+ (?P<semantic>[^:]+): (?P<data>.*)$''')

    def __init__(self, idx, f=None, layout=None, load_vertices=True):
        self.vertices = []
        self.layout = layout and layout or InputLayout()
        self.first = 0
        self.vertex_count = 0
        self.offset = 0
        self.topology = 'trianglelist'
        self.stride = 0
        self.idx = idx

        if f is not None:
            self.parse_vb_txt(f, load_vertices)

    def parse_vb_txt(self, f, load_vertices):
        split_vb_stride = 'vb%i stride:' % self.idx
        for line in map(str.strip, f):
            # print(line)
            if line.startswith('byte offset:'):
                self.offset = int(line[13:])
            if line.startswith('first vertex:'):
                self.first = int(line[14:])
            if line.startswith('vertex count:'):
                self.vertex_count = int(line[14:])
            if line.startswith('stride:'):
                self.stride = int(line[7:])
            if line.startswith(split_vb_stride):
                self.stride = int(line[len(split_vb_stride):])
            if line.startswith('element['):
                self.layout.parse_element(f)
            if line.startswith('topology:'):
                self.topology = line[10:]
                if self.topology not in supported_topologies:
                    raise Fatal('"%s" is not yet supported' % line)
            if line.startswith('vertex-data:'):
                if not load_vertices:
                    return
                self.parse_vertex_data(f)
        # If the buffer is only per-instance elements there won't be any
        # vertices. If the buffer has any per-vertex elements than we should
        # have the number of vertices declared in the header.
        if self.vertices:
            assert(len(self.vertices) == self.vertex_count)

    def parse_vb_bin(self, f, use_drawcall_range=False):
        f.seek(self.offset)
        if use_drawcall_range:
            f.seek(self.first * self.stride, 1)
        else:
            self.first = 0
        for i in itertools.count():
            if use_drawcall_range and i == self.vertex_count:
                break
            vertex = f.read(self.stride)
            if not vertex:
                break
            self.vertices.append(self.layout.decode(vertex, self.idx))
        # We intentionally disregard the vertex count when loading from a
        # binary file, as we assume frame analysis might have only dumped a
        # partial buffer to the .txt files (e.g. if this was from a dump where
        # the draw call index count was overridden it may be cut short, or
        # where the .txt files contain only sub-meshes from each draw call and
        # we are loading the .buf file because it contains the entire mesh):
        self.vertex_count = len(self.vertices)

    def append(self, vertex):
        self.vertices.append(vertex)
        self.vertex_count += 1

    def parse_vertex_data(self, f):
        vertex = {}
        for line in map(str.strip, f):
            #print(line)
            if line.startswith('instance-data:'):
                break

            match = self.vb_elem_pattern.match(line)
            if match:
                vertex[match.group('semantic')] = self.parse_vertex_element(match)
            elif line == '' and vertex:
                self.vertices.append(vertex)
                vertex = {}
        if vertex:
            self.vertices.append(vertex)

    @staticmethod
    def ms_float(val):
        x = val.split('.#')
        s = float(x[0])
        if len(x) == 1:
            return s
        if x[1].startswith('INF'):
            return s * numpy.inf # Will preserve sign
        # TODO: Differentiate between SNAN / QNAN / IND
        if s == -1: # Multiplying -1 * nan doesn't preserve sign
            return -numpy.nan # so must use unary - operator
        return numpy.nan

    def parse_vertex_element(self, match):
        fields = match.group('data').split(',')

        if self.layout[match.group('semantic')].Format.endswith('INT'):
            return tuple(map(int, fields))

        return tuple(map(self.ms_float, fields))

class VertexBufferGroup(object):
    '''
    All the per-vertex data, which may be loaded/saved from potentially
    multiple individual vertex buffers with different semantics in each.
    '''
    vb_idx_pattern = re.compile(r'''[-\.]vb([0-9]+)''')

    # Python gotcha - do not set layout=InputLayout() in the default function
    # parameters, as they would all share the *same* InputLayout since the
    # default values are only evaluated once on file load
    def __init__(self, files=None, layout=None, load_vertices=True, topology=None):
        self.vertices = []
        self.layout = layout and layout or InputLayout()
        self.first = 0
        self.vertex_count = 0
        self.topology = topology or 'trianglelist'
        self.vbs = []
        self.slots = {}

        if files is not None:
            self.parse_vb_txt(files, load_vertices)

    def parse_vb_txt(self, files, load_vertices):
        for f in files:
            match = self.vb_idx_pattern.search(f)
            if match is None:
                raise Fatal('Cannot determine vertex buffer index from filename %s' % f)
            idx = int(match.group(1))
            vb = IndividualVertexBuffer(idx, open(f, 'r'), self.layout, load_vertices)
            if vb.vertices:
                self.vbs.append(vb)
                self.slots[idx] = vb

        self.flag_invalid_semantics()

        # Non buffer specific info:
        self.first = self.vbs[0].first
        self.vertex_count = self.vbs[0].vertex_count
        self.topology = self.vbs[0].topology

        if load_vertices:
            self.merge_vbs(self.vbs)
            assert(len(self.vertices) == self.vertex_count)

    def parse_vb_bin(self, files, use_drawcall_range=False):
        for (bin_f, fmt_f) in files:
            match = self.vb_idx_pattern.search(bin_f)
            if match is not None:
                idx = int(match.group(1))
            else:
                print('Cannot determine vertex buffer index from filename %s, assuming 0 for backwards compatibility' % bin_f)
                idx = 0
            vb = IndividualVertexBuffer(idx, open(fmt_f, 'r'), self.layout, False)
            vb.parse_vb_bin(open(bin_f, 'rb'), use_drawcall_range)
            if vb.vertices:
                self.vbs.append(vb)
                self.slots[idx] = vb

        self.flag_invalid_semantics()

        # Non buffer specific info:
        self.first = self.vbs[0].first
        self.vertex_count = self.vbs[0].vertex_count
        self.topology = self.vbs[0].topology

        self.merge_vbs(self.vbs)
        assert(len(self.vertices) == self.vertex_count)

    def append(self, vertex):
        self.vertices.append(vertex)
        self.vertex_count += 1

    def remap_blendindices(self, obj, mapping):
        def lookup_vgmap(x):
            vgname = obj.vertex_groups[x].name
            return mapping.get(vgname, mapping.get(x, x))

        for vertex in self.vertices:
            for semantic in list(vertex):
                if semantic.startswith('BLENDINDICES'):
                    vertex['~' + semantic] = vertex[semantic]
                    vertex[semantic] = tuple(lookup_vgmap(x) for x in vertex[semantic])

    def revert_blendindices_remap(self):
        # Significantly faster than doing a deep copy
        for vertex in self.vertices:
            for semantic in list(vertex):
                if semantic.startswith('BLENDINDICES'):
                    vertex[semantic] = vertex['~' + semantic]
                    del vertex['~' + semantic]

    def disable_blendweights(self):
        for vertex in self.vertices:
            for semantic in list(vertex):
                if semantic.startswith('BLENDINDICES'):
                    vertex[semantic] = (0, 0, 0, 0)

    def write(self, output_prefix, strides, operator=None):
        for vbuf_idx, stride in strides.items():
            with open(output_prefix + vbuf_idx, 'wb') as output:
                for vertex in self.vertices:
                    output.write(self.layout.encode(vertex, vbuf_idx, stride))

                msg = 'Wrote %i vertices to %s' % (len(self), output.name)
                if operator:
                    operator.report({'INFO'}, msg)
                else:
                    print(msg)

    def __len__(self):
        return len(self.vertices)

    def merge_vbs(self, vbs):
        self.vertices = self.vbs[0].vertices
        del self.vbs[0].vertices
        assert(len(self.vertices) == self.vertex_count)
        for vb in self.vbs[1:]:
            assert(len(vb.vertices) == self.vertex_count)
            [ self.vertices[i].update(vertex) for i,vertex in enumerate(vb.vertices) ]
            del vb.vertices

    def merge(self, other):
        if self.layout != other.layout:
            raise Fatal('Vertex buffers have different input layouts - ensure you are only trying to merge the same vertex buffer split across multiple draw calls')
        if self.first != other.first:
            # FIXME: Future 3DMigoto might automatically set first from the
            # index buffer and chop off unreferenced vertices to save space
            raise Fatal('Cannot merge multiple vertex buffers - please check for updates of the 3DMigoto import script, or import each buffer separately')
        self.vertices.extend(other.vertices[self.vertex_count:])
        self.vertex_count = max(self.vertex_count, other.vertex_count)
        assert(len(self.vertices) == self.vertex_count)

    def wipe_semantic_for_testing(self, semantic, val=0):
        print('WARNING: WIPING %s FOR TESTING PURPOSES!!!' % semantic)
        semantic, _, components = semantic.partition('.')
        if components:
            components = [{'x':0, 'y':1, 'z':2, 'w':3}[c] for c in components]
        else:
            components = range(4)
        for vertex in self.vertices:
            for s in list(vertex):
                if s == semantic:
                    v = list(vertex[semantic])
                    for component in components:
                        if component < len(v):
                            v[component] = val
                    vertex[semantic] = v

    def flag_invalid_semantics(self):
        # This refactors some of the logic that used to be in import_vertices()
        # and get_valid_semantics() - Any semantics that re-use the same offset
        # of an earlier semantic is considered invalid and will be ignored when
        # importing the vertices. These are usually a quirk of how certain
        # engines handle unused semantics and at best will be repeating data we
        # already imported in another semantic and at worst may be
        # misinterpreting the data as a completely different type.
        #
        # Is is theoretically possible for the earlier semantic to be the
        # invalid one - if we ever encounter that we might want to allow the
        # user to choose which of the semantics sharing the same offset should
        # be considerd the valid one.
        #
        # This also makes sure the corresponding vertex buffer is present and
        # can fit the semantic.
        seen_offsets = set()
        for elem in self.layout:
            if elem.InputSlotClass != 'per-vertex':
                # Instance data isn't invalid, we just don't import it yet
                continue
            if (elem.InputSlot, elem.AlignedByteOffset) in seen_offsets:
                # Setting two flags to avoid changing behaviour in the refactor
                # - might be able to simplify this to one flag, but want to
                # test semantics that [partially] overflow the stride first,
                # and make sure that export flow (stride won't be set) works.
                elem.reused_offset = True
                elem.invalid_semantic = True
                continue
            seen_offsets.add((elem.InputSlot, elem.AlignedByteOffset))
            elem.reused_offset = False

            try:
                stride = self.slots[elem.InputSlot].stride
            except KeyError:
                # UE4 claiming it uses vertex buffers that it doesn't bind.
                elem.invalid_semantic = True
                continue

            if elem.AlignedByteOffset + format_size(elem.Format) > stride:
                elem.invalid_semantic = True
                continue

            elem.invalid_semantic = False

    def get_valid_semantics(self):
        self.flag_invalid_semantics()
        return set([elem.name for elem in self.layout
            if elem.InputSlotClass == 'per-vertex' and not elem.invalid_semantic])

class IndexBuffer(object):
    def __init__(self, *args, load_indices=True):
        self.faces = []
        self.first = 0
        self.index_count = 0
        self.format = 'DXGI_FORMAT_UNKNOWN'
        self.offset = 0
        self.topology = 'trianglelist'
        self.used_in_drawcall = None

        if isinstance(args[0], io.IOBase):
            assert(len(args) == 1)
            self.parse_ib_txt(args[0], load_indices)
        else:
            self.format, = args

        self.encoder, self.decoder = EncoderDecoder(self.format)

    def append(self, face):
        self.faces.append(face)
        self.index_count += len(face)

    def parse_ib_txt(self, f, load_indices):
        for line in map(str.strip, f):
            if line.startswith('byte offset:'):
                self.offset = int(line[13:])
                # If we see this line we are looking at a 3DMigoto frame
                # analysis dump, not a .fmt file exported by this script.
                # If it was an indexed draw call it will be followed by "first
                # index" and "index count", while if it was not an indexed draw
                # call they will be absent. So by the end of parsing:
                # used_in_drawcall = None signifies loading a .fmt file from a previous export
                # used_in_drawcall = False signifies draw call did not use the bound IB
                # used_in_drawcall = True signifies an indexed draw call
                self.used_in_drawcall = False
            if line.startswith('first index:'):
                self.first = int(line[13:])
                self.used_in_drawcall = True
            elif line.startswith('index count:'):
                self.index_count = int(line[13:])
                self.used_in_drawcall = True
            elif line.startswith('topology:'):
                self.topology = line[10:]
                if self.topology not in supported_topologies:
                    raise Fatal('"%s" is not yet supported' % line)
            elif line.startswith('format:'):
                self.format = line[8:]
            elif line == '':
                if not load_indices:
                    return
                self.parse_index_data(f)
        if self.used_in_drawcall != False:
            assert(len(self.faces) * self.indices_per_face + self.extra_indices == self.index_count)

    def parse_ib_bin(self, f, use_drawcall_range=False):
        f.seek(self.offset)
        stride = format_size(self.format)
        if use_drawcall_range:
            f.seek(self.first * stride, 1)
        else:
            self.first = 0

        face = []
        for i in itertools.count():
            if use_drawcall_range and i == self.index_count:
                break
            index = f.read(stride)
            if not index:
                break
            face.append(*self.decoder(index))
            if len(face) == self.indices_per_face:
                self.faces.append(tuple(face))
                face = []
        assert(len(face) == 0)
        self.expand_strips()

        if use_drawcall_range:
            assert(len(self.faces) * self.indices_per_face + self.extra_indices == self.index_count)
        else:
            # We intentionally disregard the index count when loading from a
            # binary file, as we assume frame analysis might have only dumped a
            # partial buffer to the .txt files (e.g. if this was from a dump where
            # the draw call index count was overridden it may be cut short, or
            # where the .txt files contain only sub-meshes from each draw call and
            # we are loading the .buf file because it contains the entire mesh):
            self.index_count = len(self.faces) * self.indices_per_face + self.extra_indices

    def parse_index_data(self, f):
        for line in map(str.strip, f):
            face = tuple(map(int, line.split()))
            assert(len(face) == self.indices_per_face)
            self.faces.append(face)
        self.expand_strips()

    def expand_strips(self):
        if self.topology == 'trianglestrip':
            # Every 2nd face has the vertices out of order to keep all faces in the same orientation:
            # https://learn.microsoft.com/en-us/windows/win32/direct3d9/triangle-strips
            self.faces = [(self.faces    [i-2][0],
                self.faces[i%2 and i   or i-1][0],
                self.faces[i%2 and i-1 or i  ][0],
            ) for i in range(2, len(self.faces)) ]
        elif self.topology == 'linestrip':
            raise Fatal('linestrip topology conversion is untested')
            self.faces = [(self.faces[i-1][0], self.faces[i][0])
                    for i in range(1, len(self.faces)) ]

    def merge(self, other):
        if self.format != other.format:
            raise Fatal('Index buffers have different formats - ensure you are only trying to merge the same index buffer split across multiple draw calls')
        self.first = min(self.first, other.first)
        self.index_count += other.index_count
        self.faces.extend(other.faces)

    def write(self, output, operator=None):
        for face in self.faces:
            output.write(self.encoder(face))

        msg = 'Wrote %i indices to %s' % (len(self), output.name)
        if operator:
            operator.report({'INFO'}, msg)
        else:
            print(msg)

    @property
    def indices_per_face(self):
        return {
            'trianglelist': 3,
            'pointlist': 1,
            'trianglestrip': 1, # + self.extra_indices for 1st tri
            'linelist': 2,
            'linestrip': 1, # + self.extra_indices for 1st line
        }[self.topology]

    @property
    def extra_indices(self):
        if len(self.faces) >= 1:
            if self.topology == 'trianglestrip':
                return 2
            if self.topology == 'linestrip':
                return 1
        return 0

    def __len__(self):
        return len(self.faces) * self.indices_per_face + self.extra_indices

def load_3dmigoto_mesh_bin(operator, vb_paths, ib_paths, pose_path):
    if len(vb_paths) != 1 or len(ib_paths) > 1:
        raise Fatal('Cannot merge meshes loaded from binary files')

    # Loading from binary files, but still need to use the .txt files as a
    # reference for the format:
    ib_bin_path, ib_txt_path = ib_paths[0]

    use_drawcall_range = False
    if hasattr(operator, 'load_buf_limit_range'): # Frame analysis import only
        use_drawcall_range = operator.load_buf_limit_range

    vb = VertexBufferGroup()
    vb.parse_vb_bin(vb_paths[0], use_drawcall_range)

    ib = None
    if ib_bin_path:
        ib = IndexBuffer(open(ib_txt_path, 'r'), load_indices=False)
        if ib.used_in_drawcall == False:
            operator.report({'WARNING'}, '{}: Discarding index buffer not used in draw call'.format(os.path.basename(ib_bin_path)))
            ib = None
        else:
            ib.parse_ib_bin(open(ib_bin_path, 'rb'), use_drawcall_range)

    return vb, ib, os.path.basename(vb_paths[0][0][0]), pose_path

def load_3dmigoto_mesh(operator, paths):
    vb_paths, ib_paths, use_bin, pose_path = zip(*paths)
    pose_path = pose_path[0]

    if use_bin[0]:
        return load_3dmigoto_mesh_bin(operator, vb_paths, ib_paths, pose_path)

    vb = VertexBufferGroup(vb_paths[0])
    # Merge additional vertex buffers for meshes split over multiple draw calls:
    for vb_path in vb_paths[1:]:
        tmp = VertexBufferGroup(vb_path)
        vb.merge(tmp)

    # For quickly testing how importent any unsupported semantics may be:
    #vb.wipe_semantic_for_testing('POSITION.w', 1.0)
    #vb.wipe_semantic_for_testing('TEXCOORD.w', 0.0)
    #vb.wipe_semantic_for_testing('TEXCOORD5', 0)
    #vb.wipe_semantic_for_testing('BINORMAL')
    #vb.wipe_semantic_for_testing('TANGENT')
    #vb.write(open(os.path.join(os.path.dirname(vb_paths[0]), 'TEST.vb'), 'wb'), operator=operator)

    ib = None
    if ib_paths and ib_paths != (None,):
        ib = IndexBuffer(open(ib_paths[0], 'r'))
        # Merge additional vertex buffers for meshes split over multiple draw calls:
        for ib_path in ib_paths[1:]:
            tmp = IndexBuffer(open(ib_path, 'r'))
            ib.merge(tmp)
        if ib.used_in_drawcall == False:
            operator.report({'WARNING'}, '{}: Discarding index buffer not used in draw call'.format(os.path.basename(ib_paths[0])))
            ib = None

    return vb, ib, os.path.basename(vb_paths[0][0]), pose_path

def normal_import_translation(elem, flip):
    unorm = elem.Format.endswith('_UNORM')
    if unorm:
        # Scale UNORM range 0:+1 to normal range -1:+1
        if flip:
            return lambda x: -(x*2.0 - 1.0)
        else:
            return lambda x: x*2.0 - 1.0
    if flip:
        return lambda x: -x
    else:
        return lambda x: x

def normal_export_translation(layout, semantic, flip):
    try:
        unorm = layout.untranslate_semantic(semantic).Format.endswith('_UNORM')
    except KeyError:
        unorm = False
    if unorm:
        # Scale normal range -1:+1 to UNORM range 0:+1
        if flip:
            return lambda x: -x/2.0 + 0.5
        else:
            return lambda x: x/2.0 + 0.5
    if flip:
        return lambda x: -x
    else:
        return lambda x: x

def import_normals_step1(mesh, data, vertex_layers, operator, translate_normal):
    # Ensure normals are 3-dimensional:
    # XXX: Assertion triggers in DOA6
    if len(data[0]) == 4:
        if [x[3] for x in data] != [0.0]*len(data):
            #raise Fatal('Normals are 4D')
            operator.report({'WARNING'}, 'Normals are 4D, storing W coordinate in NORMAL.w vertex layer. Beware that some types of edits on this mesh may be problematic.')
            vertex_layers['NORMAL.w'] = [[x[3]] for x in data]
    normals = [tuple(map(translate_normal, (x[0], x[1], x[2]))) for x in data]

    # To make sure the normals don't get lost by Blender's edit mode,
    # or mesh.update() we need to set custom normals in the loops, not
    # vertices.
    #
    # For testing, to make sure our normals are preserved let's use
    # garbage ones:
    #import random
    #normals = [(random.random() * 2 - 1,random.random() * 2 - 1,random.random() * 2 - 1) for x in normals]
    #
    # Comment from other import scripts:
    # Note: we store 'temp' normals in loops, since validate() may alter final mesh,
    #       we can only set custom lnors *after* calling it.
    mesh.create_normals_split()
    for l in mesh.loops:
        l.normal[:] = normals[l.vertex_index]

def import_normals_step2(mesh):
    # Taken from import_obj/import_fbx
    clnors = array('f', [0.0] * (len(mesh.loops) * 3))
    mesh.loops.foreach_get("normal", clnors)

    # Not sure this is still required with use_auto_smooth, but the other
    # importers do it, and at the very least it shouldn't hurt...
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))

    mesh.normals_split_custom_set(tuple(zip(*(iter(clnors),) * 3)))
    mesh.use_auto_smooth = True # This has a double meaning, one of which is to use the custom normals
    # XXX CHECKME: show_edge_sharp moved in 2.80, but I can't actually
    # recall what it does and have a feeling it was unimportant:
    #mesh.show_edge_sharp = True

def import_vertex_groups(mesh, obj, blend_indices, blend_weights):
    assert(len(blend_indices) == len(blend_weights))
    if blend_indices:
        # We will need to make sure we re-export the same blend indices later -
        # that they haven't been renumbered. Not positive whether it is better
        # to use the vertex group index, vertex group name or attach some extra
        # data. Make sure the indices and names match:
        num_vertex_groups = max(itertools.chain(*itertools.chain(*blend_indices.values()))) + 1
        for i in range(num_vertex_groups):
            obj.vertex_groups.new(name=str(i))
        for vertex in mesh.vertices:
            for semantic_index in sorted(blend_indices.keys()):
                for i, w in zip(blend_indices[semantic_index][vertex.index], blend_weights[semantic_index][vertex.index]):
                    if w == 0.0:
                        continue
                    obj.vertex_groups[i].add((vertex.index,), w, 'REPLACE')
def import_uv_layers(mesh, obj, texcoords, flip_texcoord_v):
    for (texcoord, data) in sorted(texcoords.items()):
        # TEXCOORDS can have up to four components, but UVs can only have two
        # dimensions. Not positive of the best way to handle this in general,
        # but for now I'm thinking that splitting the TEXCOORD into two sets of
        # UV coordinates might work:
        dim = len(data[0])
        if dim == 4:
            components_list = ('xy', 'zw')
        elif dim == 3:
            components_list = ('xy', 'z')
        elif dim == 2:
            components_list = ('xy',)
        elif dim == 1:
            components_list = ('x',)
        else:
            raise Fatal('Unhandled TEXCOORD%s dimension: %i' % (texcoord, dim))
        cmap = {'x': 0, 'y': 1, 'z': 2, 'w': 3}

        for components in components_list:
            uv_name = 'TEXCOORD%s.%s' % (texcoord and texcoord or '', components)
            if hasattr(mesh, 'uv_textures'): # 2.79
                mesh.uv_textures.new(uv_name)
            else: # 2.80
                mesh.uv_layers.new(name=uv_name)
            blender_uvs = mesh.uv_layers[uv_name]

            # This will assign a texture to the UV layer, which works fine but
            # working out which texture maps to which UV layer is guesswork
            # before the import and the artist may as well just assign it
            # themselves in the UV editor pane when they can see the unwrapped
            # mesh to compare it with the dumped textures:
            #
            #path = textures.get(uv_layer, None)
            #if path is not None:
            #    image = load_image(path)
            #    for i in range(len(mesh.polygons)):
            #        mesh.uv_textures[uv_layer].data[i].image = image

            # Can't find an easy way to flip the display of V in Blender, so
            # add an option to flip it on import & export:
            if (len(components) % 2 == 1):
                # 1D or 3D TEXCOORD, save in a UV layer with V=0
                translate_uv = lambda u: (u[0], 0)
            elif flip_texcoord_v:
                translate_uv = lambda uv: (uv[0], 1.0 - uv[1])
                # Record that V was flipped so we know to undo it when exporting:
                obj['3DMigoto:' + uv_name] = {'flip_v': True}
            else:
                translate_uv = lambda uv: uv

            uvs = [[d[cmap[c]] for c in components] for d in data]
            for l in mesh.loops:
                blender_uvs.data[l.index].uv = translate_uv(uvs[l.vertex_index])

def new_custom_attribute_int(mesh, layer_name):
    # vertex_layers were dropped in 4.0. Looks like attributes were added in
    # 3.0 (to confirm), so we could probably start using them or add a
    # migration function on older versions as well
    if bpy.app.version >= (4, 0):
        mesh.attributes.new(name=layer_name, type='INT', domain='POINT')
        return mesh.attributes[layer_name]
    else:
        mesh.vertex_layers_int.new(name=layer_name)
        return mesh.vertex_layers_int[layer_name]

def new_custom_attribute_float(mesh, layer_name):
    if bpy.app.version >= (4, 0):
        # TODO: float2 and float3 could be stored directly as 'FLOAT2' /
        # 'FLOAT_VECTOR' types (in fact, UV layers in 4.0 show up in attributes
        # using FLOAT2) instead of saving each component as a separate layer.
        # float4 is missing though. For now just get it working equivelently to
        # the old vertex layers.
        mesh.attributes.new(name=layer_name, type='FLOAT', domain='POINT')
        return mesh.attributes[layer_name]
    else:
        mesh.vertex_layers_float.new(name=layer_name)
        return mesh.vertex_layers_float[layer_name]

# TODO: Refactor to prefer attributes over vertex layers even on 3.x if they exist
def custom_attributes_int(mesh):
    if bpy.app.version >= (4, 0):
        return { k: v for k,v in mesh.attributes.items()
                if (v.data_type, v.domain) == ('INT', 'POINT') }
    else:
        return mesh.vertex_layers_int

def custom_attributes_float(mesh):
    if bpy.app.version >= (4, 0):
        return { k: v for k,v in mesh.attributes.items()
                if (v.data_type, v.domain) == ('FLOAT', 'POINT') }
    else:
        return mesh.vertex_layers_float

# This loads unknown data from the vertex buffers as vertex layers
def import_vertex_layers(mesh, obj, vertex_layers):
    for (element_name, data) in sorted(vertex_layers.items()):
        dim = len(data[0])
        cmap = {0: 'x', 1: 'y', 2: 'z', 3: 'w'}
        for component in range(dim):

            if dim != 1 or element_name.find('.') == -1:
                layer_name = '%s.%s' % (element_name, cmap[component])
            else:
                layer_name = element_name

            if type(data[0][0]) == int:
                layer = new_custom_attribute_int(mesh, layer_name)
                for v in mesh.vertices:
                    val = data[v.index][component]
                    # Blender integer layers are 32bit signed and will throw an
                    # exception if we are assigning an unsigned value that
                    # can't fit in that range. Reinterpret as signed if necessary:
                    if val < 0x80000000:
                        layer.data[v.index].value = val
                    else:
                        layer.data[v.index].value = struct.unpack('i', struct.pack('I', val))[0]
            elif type(data[0][0]) == float:
                layer = new_custom_attribute_float(mesh, layer_name)
                for v in mesh.vertices:
                    layer.data[v.index].value = data[v.index][component]
            else:
                raise Fatal('BUG: Bad layer type %s' % type(data[0][0]))

def import_faces_from_ib(mesh, ib, flip_winding):
    mesh.loops.add(len(ib.faces) * 3)
    mesh.polygons.add(len(ib.faces))
    if flip_winding:
        mesh.loops.foreach_set('vertex_index', unpack_list(map(reversed, ib.faces)))
    else:
        mesh.loops.foreach_set('vertex_index', unpack_list(ib.faces))
    mesh.polygons.foreach_set('loop_start', [x*3 for x in range(len(ib.faces))])
    mesh.polygons.foreach_set('loop_total', [3] * len(ib.faces))

def import_faces_from_vb_trianglelist(mesh, vb, flip_winding):
    # Only lightly tested
    num_faces = len(vb.vertices) // 3
    mesh.loops.add(num_faces * 3)
    mesh.polygons.add(num_faces)
    if flip_winding:
        raise Fatal('Flipping winding order untested without index buffer') # export in particular needs support
        mesh.loops.foreach_set('vertex_index', [x for x in reversed(range(num_faces * 3))])
    else:
        mesh.loops.foreach_set('vertex_index', [x for x in range(num_faces * 3)])
    mesh.polygons.foreach_set('loop_start', [x*3 for x in range(num_faces)])
    mesh.polygons.foreach_set('loop_total', [3] * num_faces)

def import_faces_from_vb_trianglestrip(mesh, vb, flip_winding):
    # Only lightly tested
    if flip_winding:
        raise Fatal('Flipping winding order with triangle strip topology is not implemented')
    num_faces = len(vb.vertices) - 2
    if num_faces <= 0:
        raise Fatal('Insufficient vertices in trianglestrip')
    mesh.loops.add(num_faces * 3)
    mesh.polygons.add(num_faces)

    # Every 2nd face has the vertices out of order to keep all faces in the same orientation:
    # https://learn.microsoft.com/en-us/windows/win32/direct3d9/triangle-strips
    tristripindex = [( i,
        i%2 and i+2 or i+1,
        i%2 and i+1 or i+2,
    ) for i in range(num_faces) ]

    mesh.loops.foreach_set('vertex_index', unpack_list(tristripindex))
    mesh.polygons.foreach_set('loop_start', [x*3 for x in range(num_faces)])
    mesh.polygons.foreach_set('loop_total', [3] * num_faces)

def import_vertices(mesh, obj, vb, operator, semantic_translations={}, flip_normal=False):
    mesh.vertices.add(len(vb.vertices))

    blend_indices = {}
    blend_weights = {}
    texcoords = {}
    vertex_layers = {}
    use_normals = False

    for elem in vb.layout:
        if elem.InputSlotClass != 'per-vertex' or elem.reused_offset:
            continue

        if elem.InputSlot not in vb.slots:
            # UE4 known to proclaim it has attributes in all the slots in the
            # layout description, but only ends up using two (and one of those
            # is per-instance data)
            print('NOTICE: Vertex semantic %s unavailable due to missing vb%i' % (elem.name, elem.InputSlot))
            continue

        translated_elem_name, translated_elem_index = \
                semantic_translations.get(elem.name, (elem.name, elem.SemanticIndex))

        # Some games don't follow the official DirectX UPPERCASE semantic naming convention:
        translated_elem_name = translated_elem_name.upper()

        data = tuple( x[elem.name] for x in vb.vertices )
        if translated_elem_name == 'POSITION':
            # Ensure positions are 3-dimensional:
            if len(data[0]) == 4:
                if ([x[3] for x in data] != [1.0]*len(data)):
                    # XXX: There is a 4th dimension in the position, which may
                    # be some artibrary custom data, or maybe something weird
                    # is going on like using Homogeneous coordinates in a
                    # vertex buffer. The meshes this triggers on in DOA6
                    # (skirts) lie about almost every semantic and we cannot
                    # import them with this version of the script regardless.
                    # But perhaps in some cases it might still be useful to be
                    # able to import as much as we can and just preserve this
                    # unknown 4th dimension to export it later or have a game
                    # specific script perform some operations on it - so we
                    # store it in a vertex layer and warn the modder.
                    operator.report({'WARNING'}, 'Positions are 4D, storing W coordinate in POSITION.w vertex layer. Beware that some types of edits on this mesh may be problematic.')
                    vertex_layers['POSITION.w'] = [[x[3]] for x in data]
            positions = [(x[0], x[1], x[2]) for x in data]
            mesh.vertices.foreach_set('co', unpack_list(positions))
        elif translated_elem_name.startswith('COLOR'):
            if len(data[0]) <= 3 or vertex_color_layer_channels == 4:
                # Either a monochrome/RGB layer, or Blender 2.80 which uses 4
                # channel layers
                mesh.vertex_colors.new(name=elem.name)
                color_layer = mesh.vertex_colors[elem.name].data
                c = vertex_color_layer_channels
                for l in mesh.loops:
                    color_layer[l.index].color = list(data[l.vertex_index]) + [0]*(c-len(data[l.vertex_index]))
            else:
                mesh.vertex_colors.new(name=elem.name + '.RGB')
                mesh.vertex_colors.new(name=elem.name + '.A')
                color_layer = mesh.vertex_colors[elem.name + '.RGB'].data
                alpha_layer = mesh.vertex_colors[elem.name + '.A'].data
                for l in mesh.loops:
                    color_layer[l.index].color = data[l.vertex_index][:3]
                    alpha_layer[l.index].color = [data[l.vertex_index][3], 0, 0]
        elif translated_elem_name == 'NORMAL':
            use_normals = True
            translate_normal = normal_import_translation(elem, flip_normal)
            import_normals_step1(mesh, data, vertex_layers, operator, translate_normal)
        elif translated_elem_name in ('TANGENT', 'BINORMAL'):
        #    # XXX: loops.tangent is read only. Not positive how to handle
        #    # this, or if we should just calculate it when re-exporting.
        #    for l in mesh.loops:
        #        FIXME: rescale range if elem.Format.endswith('_UNORM')
        #        assert(data[l.vertex_index][3] in (1.0, -1.0))
        #        l.tangent[:] = data[l.vertex_index][0:3]
            operator.report({'INFO'}, 'Skipping import of %s in favour of recalculating on export' % elem.name)
        elif translated_elem_name.startswith('BLENDINDICES'):
            blend_indices[translated_elem_index] = data
        elif translated_elem_name.startswith('BLENDWEIGHT'):
            blend_weights[translated_elem_index] = data
        elif translated_elem_name.startswith('TEXCOORD') and elem.is_float():
            texcoords[translated_elem_index] = data
        else:
            operator.report({'INFO'}, 'Storing unhandled semantic %s %s as vertex layer' % (elem.name, elem.Format))
            vertex_layers[elem.name] = data

    return (blend_indices, blend_weights, texcoords, vertex_layers, use_normals)

def import_3dmigoto(operator, context, paths, merge_meshes=True, **kwargs):
    if merge_meshes:
        return import_3dmigoto_vb_ib(operator, context, paths, **kwargs)
    else:
        obj = []
        for p in paths:
            try:
                obj.append(import_3dmigoto_vb_ib(operator, context, [p], **kwargs))
            except Fatal as e:
                operator.report({'ERROR'}, str(e) + ': ' + str(p[:2]))
        # FIXME: Group objects together
        return obj

def assert_pointlist_ib_is_pointless(ib, vb):
    # Index Buffers are kind of pointless with point list topologies, because
    # the advantages they offer for triangle list topologies don't really
    # apply and there is little point in them being used at all... But, there
    # is nothing technically stopping an engine from using them regardless, and
    # we do see this in One Piece Burning Blood. For now, just verify that the
    # index buffers are the trivial case that lists every vertex in order, and
    # just ignore them since we already loaded the vertex buffer in that order.
    assert(len(vb) == len(ib)) # FIXME: Properly implement point list index buffers
    assert(all([(i,) == j for i,j in enumerate(ib.faces)])) # FIXME: Properly implement point list index buffers

# NOTE: The group names in this regex will get added as custom data on the
# blender object if they match, like "3DMigoto:VBHash"
# FIXME: test hash contamination warnings or other settings (e.g. filename_reg,
# hold) that can affect filename to make sure this regex is ok. XXX: If there
# is a hash contamination warning present, reinjection will be unreliable - we
# should maybe warn about that
fa_filename_hash_pattern = re.compile(r'''
        (?:-vb[0-9]+(?P<VBHashContamination>=![MUCS]+!)?=(?P<VBHash>[0-9a-f]+))?
        (?:-vs=(?P<VSHash>[0-9a-f]+))?
        (?:-hs=(?P<HSHash>[0-9a-f]+))?
        (?:-ds=(?P<DSHash>[0-9a-f]+))?
        (?:-gs=(?P<GSHash>[0-9a-f]+))?
        (?:-ps=(?P<PSHash>[0-9a-f]+))?
        (?:\.|$)
        ''', re.VERBOSE | re.IGNORECASE)

def import_3dmigoto_vb_ib(operator, context, paths, flip_texcoord_v=True, flip_winding=False, flip_normal=False, axis_forward='-Z', axis_up='Y', pose_cb_off=[0,0], pose_cb_step=1):
    vb, ib, name, pose_path = load_3dmigoto_mesh(operator, paths)

    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(mesh.name, mesh)

    global_matrix = axis_conversion(from_forward=axis_forward, from_up=axis_up).to_4x4()
    obj.matrix_world = global_matrix

    if hasattr(operator.properties, 'semantic_remap'):
        semantic_translations = vb.layout.apply_semantic_remap(operator)
    else:
        semantic_translations = vb.layout.get_semantic_remap()

    # Attach the vertex buffer layout to the object for later exporting. Can't
    # seem to retrieve this if attached to the mesh - to_mesh() doesn't copy it:
    obj['3DMigoto:VBLayout'] = vb.layout.serialise()
    obj['3DMigoto:Topology'] = vb.topology
    for raw_vb in vb.vbs:
        obj['3DMigoto:VB%iStride' % raw_vb.idx] = raw_vb.stride
    obj['3DMigoto:FirstVertex'] = vb.first
    # Record these import options so the exporter can set them to match by
    # default. Might also consider adding them to the .fmt file so reimporting
    # a previously exported file can also set them by default?
    obj['3DMigoto:FlipWinding'] = flip_winding
    obj['3DMigoto:FlipNormal'] = flip_normal
    # Store hashes for .ini mod generation when exporting
    hash_match = fa_filename_hash_pattern.search(name)
    if hash_match:
        for group,value in hash_match.groupdict().items():
            if value:
                obj['3DMigoto:'+group] = value

    if ib is not None:
        if ib.topology in ('trianglelist', 'trianglestrip'):
            import_faces_from_ib(mesh, ib, flip_winding)
        elif ib.topology == 'pointlist':
            assert_pointlist_ib_is_pointless(ib, vb)
        else:
            raise Fatal('Unsupported topology (IB): {}'.format(ib.topology))
        # Attach the index buffer layout to the object for later exporting.
        obj['3DMigoto:IBFormat'] = ib.format
        obj['3DMigoto:FirstIndex'] = ib.first
    elif vb.topology == 'trianglelist':
        import_faces_from_vb_trianglelist(mesh, vb, flip_winding)
    elif vb.topology == 'trianglestrip':
        import_faces_from_vb_trianglestrip(mesh, vb, flip_winding)
    elif vb.topology != 'pointlist':
        raise Fatal('Unsupported topology (VB): {}'.format(vb.topology))
    if vb.topology == 'pointlist':
        operator.report({'WARNING'}, '{}: uses point list topology, which is highly experimental and may have issues with normals/tangents/lighting. This may not be the mesh you are looking for.'.format(mesh.name))

    (blend_indices, blend_weights, texcoords, vertex_layers, use_normals) = import_vertices(mesh, obj, vb, operator, semantic_translations, flip_normal)

    import_uv_layers(mesh, obj, texcoords, flip_texcoord_v)
    if not texcoords:
        operator.report({'WARNING'}, '{}: No TEXCOORDs / UV layers imported. This may cause issues with normals/tangents/lighting on export.'.format(mesh.name))

    import_vertex_layers(mesh, obj, vertex_layers)

    import_vertex_groups(mesh, obj, blend_indices, blend_weights)

    # Validate closes the loops so they don't disappear after edit mode and probably other important things:
    mesh.validate(verbose=False, clean_customdata=False)  # *Very* important to not remove lnors here!
    # Not actually sure update is necessary. It seems to update the vertex normals, not sure what else:
    mesh.update()

    # Must be done after validate step:
    if use_normals:
        import_normals_step2(mesh)
    elif hasattr(mesh, 'calc_normals'): # Dropped in Blender 4.0
        mesh.calc_normals()

    link_object_to_scene(context, obj)
    select_set(obj, True)
    set_active_object(context, obj)

    if pose_path is not None:
        import_pose(operator, context, pose_path, limit_bones_to_vertex_groups=True,
                axis_forward=axis_forward, axis_up=axis_up,
                pose_cb_off=pose_cb_off, pose_cb_step=pose_cb_step)
        set_active_object(context, obj)

    return obj

# from export_obj:
def mesh_triangulate(me):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()

def blender_vertex_to_3dmigoto_vertex(mesh, obj, blender_loop_vertex, layout, texcoords, blender_vertex, translate_normal, translate_tangent):
    if blender_loop_vertex is not None:
        blender_vertex = mesh.vertices[blender_loop_vertex.vertex_index]
    vertex = {}

    # TODO: Warn if vertex is in too many vertex groups for this layout,
    # ignoring groups with weight=0.0
    vertex_groups = sorted(blender_vertex.groups, key=lambda x: x.weight, reverse=True)

    for elem in layout:
        if elem.InputSlotClass != 'per-vertex' or elem.reused_offset:
            continue

        semantic_translations = layout.get_semantic_remap()
        translated_elem_name, translated_elem_index = \
                semantic_translations.get(elem.name, (elem.name, elem.SemanticIndex))

        # Some games don't follow the official DirectX UPPERCASE semantic naming convention:
        translated_elem_name = translated_elem_name.upper()

        if translated_elem_name == 'POSITION':
            if 'POSITION.w' in custom_attributes_float(mesh):
                vertex[elem.name] = list(blender_vertex.undeformed_co) + \
                                        [custom_attributes_float(mesh)['POSITION.w'].data[blender_vertex.index].value]
            else:
                vertex[elem.name] = elem.pad(list(blender_vertex.undeformed_co), 1.0)
        elif translated_elem_name.startswith('COLOR'):
            if elem.name in mesh.vertex_colors:
                vertex[elem.name] = elem.clip(list(mesh.vertex_colors[elem.name].data[blender_loop_vertex.index].color))
            else:
                vertex[elem.name] = list(mesh.vertex_colors[elem.name+'.RGB'].data[blender_loop_vertex.index].color)[:3] + \
                                        [mesh.vertex_colors[elem.name+'.A'].data[blender_loop_vertex.index].color[0]]
        elif translated_elem_name == 'NORMAL':
            if 'NORMAL.w' in custom_attributes_float(mesh):
                vertex[elem.name] = list(map(translate_normal, blender_loop_vertex.normal)) + \
                                        [custom_attributes_float(mesh)['NORMAL.w'].data[blender_vertex.index].value]
            elif blender_loop_vertex:
                vertex[elem.name] = elem.pad(list(map(translate_normal, blender_loop_vertex.normal)), 0.0)
            else:
                # XXX: point list topology, these normals are probably going to be pretty poor, but at least it's something to export
                vertex[elem.name] = elem.pad(list(map(translate_normal, blender_vertex.normal)), 0.0)
        elif translated_elem_name.startswith('TANGENT'):
            # DOAXVV has +1/-1 in the 4th component. Not positive what this is,
            # but guessing maybe the bitangent sign? Not even sure it is used...
            # FIXME: Other games
            if blender_loop_vertex:
                vertex[elem.name] = elem.pad(list(map(translate_tangent, blender_loop_vertex.tangent)), blender_loop_vertex.bitangent_sign)
            else:
                # XXX Blender doesn't save tangents outside of loops, so unless
                # we save these somewhere custom when importing they are
                # effectively lost. We could potentially calculate a tangent
                # from blender_vertex.normal, but there is probably little
                # point given that normal will also likely be garbage since it
                # wasn't imported from the mesh.
                pass
        elif translated_elem_name.startswith('BINORMAL'):
            # Some DOA6 meshes (skirts) use BINORMAL, but I'm not certain it is
            # actually the binormal. These meshes are weird though, since they
            # use 4 dimensional positions and normals, so they aren't something
            # we can really deal with at all. Therefore, the below is untested,
            # FIXME: So find a mesh where this is actually the binormal,
            # uncomment the below code and test.
            # normal = blender_loop_vertex.normal
            # tangent = blender_loop_vertex.tangent
            # binormal = numpy.cross(normal, tangent)
            # XXX: Does the binormal need to be normalised to a unit vector?
            # binormal = binormal / numpy.linalg.norm(binormal)
            # vertex[elem.name] = elem.pad(list(map(translate_binormal, binormal)), 0.0)
            pass
        elif translated_elem_name.startswith('BLENDINDICES'):
            i = translated_elem_index * 4
            vertex[elem.name] = elem.pad([ x.group for x in vertex_groups[i:i+4] ], 0)
        elif translated_elem_name.startswith('BLENDWEIGHT'):
            # TODO: Warn if vertex is in too many vertex groups for this layout
            i = translated_elem_index * 4
            vertex[elem.name] = elem.pad([ x.weight for x in vertex_groups[i:i+4] ], 0.0)
        elif translated_elem_name.startswith('TEXCOORD') and elem.is_float():
            uvs = []
            for uv_name in ('%s.xy' % elem.remapped_name, '%s.zw' % elem.remapped_name):
                if uv_name in texcoords:
                    uvs += list(texcoords[uv_name][blender_loop_vertex.index])
            # Handle 1D + 3D TEXCOORDs. Order is important - 1D TEXCOORDs won't
            # match anything in above loop so only .x below, 3D TEXCOORDS will
            # have processed .xy part above, and .z part below
            for uv_name in ('%s.x' % elem.remapped_name, '%s.z' % elem.remapped_name):
                if uv_name in texcoords:
                    uvs += [texcoords[uv_name][blender_loop_vertex.index].x]
            vertex[elem.name] = uvs
        else:
            # Unhandled semantics are saved in vertex layers
            data = []
            for component in 'xyzw':
                layer_name = '%s.%s' % (elem.name, component)
                if layer_name in custom_attributes_int(mesh):
                    data.append(custom_attributes_int(mesh)[layer_name].data[blender_vertex.index].value)
                elif layer_name in custom_attributes_float(mesh):
                    data.append(custom_attributes_float(mesh)[layer_name].data[blender_vertex.index].value)
            if data:
                #print('Retrieved unhandled semantic %s %s from vertex layer' % (elem.name, elem.Format), data)
                vertex[elem.name] = data

        if elem.name not in vertex:
            print('NOTICE: Unhandled vertex element: %s' % elem.name)
        #else:
        #    print('%s: %s' % (elem.name, repr(vertex[elem.name])))

    return vertex

def write_fmt_file(f, vb, ib, strides):
    for vbuf_idx, stride in strides.items():
        if vbuf_idx.isnumeric():
            f.write('vb%s stride: %i\n' % (vbuf_idx, stride))
        else:
            f.write('stride: %i\n' % stride)
    f.write('topology: %s\n' % vb.topology)
    if ib is not None:
        f.write('format: %s\n' % ib.format)
    f.write(vb.layout.to_string())

def write_ini_file(f, vb, vb_path, ib, ib_path, strides, obj, topology, override_vertex_shader, texture_override_range):
    # FIXME: backup is something that needs to be decided in tandem with what
    # we finalise writing in the ShaderOverride sections. The safe option is
    # to always turn it on, and if the only thing we write to the
    # ShaderOverride is checktextureoverride=vb0 we absolutely should enable
    # it, but if we instead have the ShaderOverride call a command list in the
    # base mod that has been properly set up with a command list that already
    # does the backup + restore already this will be redundant.
    backup = False
    #topology='trianglestrip' # Testing
    bind_section = ''
    backup_section = ''
    restore_section = ''
    resource_section = ''
    resource_bak_section = ''

    #Prepare sections
    draw_section = 'handling = skip\n'
    if ib is not None:
        draw_section += 'drawindexed = auto\n'
    else:
        draw_section += 'draw = auto\n'

    if ib is not None:
        bind_section += 'ib = ResourceIB\n'
        resource_section += textwrap.dedent('''
            [ResourceIB]
            type = buffer
            format = {}
            filename = {}
            ''').format(ib.format, os.path.basename(ib_path))
        if backup:
            resource_bak_section += '[ResourceBakIB]\n'
            backup_section += 'ResourceBakIB = ref ib\n'
            restore_section += 'ib = ResourceBakIB\n'

    for vbuf_idx, stride in strides.items():
        bind_section += 'vb{0} = ResourceVB{0}\n'.format(vbuf_idx or 0)
        resource_section += textwrap.dedent('''
            [ResourceVB{}]
            type = buffer
            stride = {}
            filename = {}
            ''').format(vbuf_idx, stride, os.path.basename(vb_path + vbuf_idx))
        if backup:
            resource_bak_section += '[ResourceBakVB{0}]\n'.format(vbuf_idx or 0)
            backup_section += 'ResourceBakVB{0} = ref vb{0}\n'.format(vbuf_idx or 0)
            restore_section += 'vb{0} = ResourceBakVB{0}\n'.format(vbuf_idx or 0)

    #Write ShaderOverrides file
    shader_overrides_path = os.path.dirname(os.path.dirname(f.name)) + r'\_ShaderOverrides'
    if not os.path.exists(shader_overrides_path):
        os.makedirs(shader_overrides_path)

    if override_vertex_shader:
        shader_hash_to_write = obj['3DMigoto:VSHash']
    else:
        shader_hash_to_write = obj['3DMigoto:PSHash']

    shader_overrides_file = shader_overrides_path + '\\' + shader_hash_to_write + '.ini'

    # FIXME: THIS NEEDS MAJOR REWORK!
    # - This should not be installing to some arbitrary parent directory. At
    #   worst this should be selected by the user, at best we would find a way to
    #   make this work without the need to write to some central folder at all.
    # - This risks creating hidden conflicts between mods, e.g. What happens if
    #   modder 1 selects 4 textures, then modder 2 selects 1 texture? Now we
    #   have a conflict and the user might break mod 1 by installing mod 2.
    # - The modder will have to remember to package up files from a different
    #   directory to the one they are working in
    # - The users will have to extract the mods to the correct directories, or
    #   they will end up asking why they are getting mod conflict warnings from
    #   3DMigoto. We have tried to minimise the need for users to get this right
    # - Depending on how the game's base mod has been set up this may need (and
    #   is highly recommended to) run a command list that decides what to do
    #   (e.g. add support for toggle keys, frame analysis, texture slot
    #   overrides, etc) instead of directly calling checktextureoverride
    # - My preferred solution is to allow each mod to add their hashes to an
    #   existing set, but that will require an update to 3DMigoto.
    # - TODO: Can we do this without 3DMigoto updates? The central directory
    #   would achive that, but I don't think it's a significant improvement
    #   over the current central d3dx.ini and brings it's own problems that
    #   make it pretty questionable as something we want to support long term,
    #   but may be useful as a stop-gap measure.
    #
    #   TODO: Investigate how existing 3DMigoto code would handle files with
    #   duplicated namespace overrides (i.e. instead of a central directory,
    #   can we use a common namespace?) and a duplicate ShaderOverride in that
    #   namespace. Also, handling=abort works much like a return statement and
    #   could potentially be useful to prevent additional ShaderOverrides with
    #   the same hash from running (though that also brings risks of mod
    #   conflicts if it prevents something important running in another mod).
    #
    #   Again, my STRONGLY preferred solution is simply to add support to
    #   3DMigoto instead of trying to work around its current limitations.
    #     -DarkStarSword
    #
    #with open(shader_overrides_file, 'w') as f_overrides:
    #    f_overrides.write(textwrap.dedent('''
    #        [ShaderOverride]
    #        hash = {}
    #        checktextureoverride = vb0
    #        ''').format(shader_hash_to_write))
    #    for n in range(texture_override_range + 1):
    #        f_overrides.write('checktextureoverride = ps-t{}\n'.format(n))

    #Write Mod files
    # FIXME: Test if no pixel shader hash present (think this is broken elsewhere)
    # FIXME: Vertex should be listed before Pixel - stick to pipeline order!
    # FIXME: Hull, Domain, Geometry...
    # FIXME: Finalise ShaderOverride location and adjust message
    f.write(textwrap.dedent('''
        ;Automatically generated file.
        ;This export had the following shader hashes:
        ;Pixel Shader = {ps}
        ;Vertex Shader = {vs}
        ;One of them has been automatically saved inside Mods/_ShaderOverrides.
        ;It is required for your mod to work.

        ;------Mesh swaps section------
        [TextureOverride_{vb}]
        hash = {vb}
        ''').lstrip().format(
            ps=obj['3DMigoto:PSHash'],
            vs=obj['3DMigoto:VSHash'],
            vb=obj['3DMigoto:VBHash']))

    if ib is not None and '3DMigoto:FirstIndex' in obj:
        f.write('match_first_index = {}\n'.format(obj['3DMigoto:FirstIndex']))
    elif ib is None and '3DMigoto:FirstVertex' in obj:
        f.write('match_first_vertex = {}\n'.format(obj['3DMigoto:FirstVertex']))

    if backup:
        f.write(backup_section)

    f.write(bind_section)

    if topology == 'trianglestrip':
        f.write('run = CustomShaderOverrideTopology\n')
    else:
        f.write(draw_section)

    if backup:
        f.write(restore_section)

    if topology == 'trianglestrip':
        f.write(textwrap.dedent('''
            [CustomShaderOverrideTopology]
            topology = triangle_list
            ''') + draw_section)

    if backup:
        f.write('\n' + resource_bak_section)

    f.write(resource_section)

    #Sample texture_mods_section
    f.write(textwrap.dedent('''
    ;------Texture swaps section------
    ;[TextureOverride_SwapSample]
    ;hash =
    ;ps-t0 = Resource_SwapSample
    ;[Resource_SwapSample]
    ;filename = mytexture.png
    '''))

def export_3dmigoto(operator, context, vb_path, ib_path, fmt_path, ini_path):
    obj = context.object

    if obj is None:
        raise Fatal('No object selected')

    strides = {x[11:-6]: obj[x] for x in obj.keys() if x.startswith('3DMigoto:VB') and x.endswith('Stride')}
    layout = InputLayout(obj['3DMigoto:VBLayout'])
    orig_topology = topology = 'trianglelist'
    if '3DMigoto:Topology' in obj:
        topology = obj['3DMigoto:Topology']
        if topology == 'trianglestrip':
            operator.report({'WARNING'}, 'trianglestrip topology not supported for export, and has been converted to trianglelist. Override draw call topology using a [CustomShader] section with topology=triangle_list')
            topology = 'trianglelist'
    if hasattr(context, "evaluated_depsgraph_get"): # 2.80
        mesh = obj.evaluated_get(context.evaluated_depsgraph_get()).to_mesh()
    else: # 2.79
        mesh = obj.to_mesh(context.scene, True, 'PREVIEW', calc_tessface=False)
    mesh_triangulate(mesh)

    try:
        ib_format = obj['3DMigoto:IBFormat']
    except KeyError:
        ib = None
    else:
        ib = IndexBuffer(ib_format)

    # Calculates tangents and makes loop normals valid (still with our
    # custom normal data from import time):
    try:
        mesh.calc_tangents()
    except RuntimeError as e:
        operator.report({'WARNING'}, 'Tangent calculation failed, the exported mesh may have bad normals/tangents/lighting. Original {}'.format(str(e)))

    texcoord_layers = {}
    for uv_layer in mesh.uv_layers:
        texcoords = {}

        try:
            flip_texcoord_v = obj['3DMigoto:' + uv_layer.name]['flip_v']
            if flip_texcoord_v:
                flip_uv = lambda uv: (uv[0], 1.0 - uv[1])
            else:
                flip_uv = lambda uv: uv
        except KeyError:
            flip_uv = lambda uv: uv

        for l in mesh.loops:
            uv = flip_uv(uv_layer.data[l.index].uv)
            texcoords[l.index] = uv
        texcoord_layers[uv_layer.name] = texcoords

    translate_normal = normal_export_translation(layout, 'NORMAL', operator.flip_normal)
    translate_tangent = normal_export_translation(layout, 'TANGENT', operator.flip_tangent)

    # Blender's vertices have unique positions, but may have multiple
    # normals, tangents, UV coordinates, etc - these are stored in the
    # loops. To export back to DX we need these combined together such that
    # a vertex is a unique set of all attributes, but we don't want to
    # completely blow this out - we still want to reuse identical vertices
    # via the index buffer. There might be a convenience function in
    # Blender to do this, but it's easy enough to do this ourselves
    indexed_vertices = collections.OrderedDict()
    vb = VertexBufferGroup(layout=layout, topology=topology)
    vb.flag_invalid_semantics()
    if vb.topology == 'trianglelist':
        for poly in mesh.polygons:
            face = []
            for blender_lvertex in mesh.loops[poly.loop_start:poly.loop_start + poly.loop_total]:
                vertex = blender_vertex_to_3dmigoto_vertex(mesh, obj, blender_lvertex, layout, texcoord_layers, None, translate_normal, translate_tangent)
                if ib is not None:
                    face.append(indexed_vertices.setdefault(HashableVertex(vertex), len(indexed_vertices)))
                else:
                    if operator.flip_winding:
                        raise Fatal('Flipping winding order without index buffer not implemented')
                    vb.append(vertex)
            if ib is not None:
                if operator.flip_winding:
                    face.reverse()
                ib.append(face)

        if ib is not None:
            for vertex in indexed_vertices:
                vb.append(vertex)
    elif vb.topology == 'pointlist':
        for index, blender_vertex in enumerate(mesh.vertices):
            vb.append(blender_vertex_to_3dmigoto_vertex(mesh, obj, None, layout, texcoord_layers, blender_vertex, translate_normal, translate_tangent))
            if ib is not None:
                ib.append((index,))
    else:
        raise Fatal('topology "%s" is not supported for export' % vb.topology)

    vgmaps = {k[15:]:keys_to_ints(v) for k,v in obj.items() if k.startswith('3DMigoto:VGMap:')}

    if '' not in vgmaps:
        vb.write(vb_path, strides, operator=operator)

    base, ext = os.path.splitext(vb_path)
    for (suffix, vgmap) in vgmaps.items():
        ib_path = vb_path
        if suffix:
            ib_path = '%s-%s%s' % (base, suffix, ext)
        vgmap_path = os.path.splitext(ib_path)[0] + '.vgmap'
        print('Exporting %s...' % ib_path)
        vb.remap_blendindices(obj, vgmap)
        vb.write(ib_path, strides, operator=operator)
        vb.revert_blendindices_remap()
        sorted_vgmap = collections.OrderedDict(sorted(vgmap.items(), key=lambda x:x[1]))
        json.dump(sorted_vgmap, open(vgmap_path, 'w'), indent=2)

    if ib is not None:
        ib.write(open(ib_path, 'wb'), operator=operator)

    # Write format reference file
    write_fmt_file(open(fmt_path, 'w'), vb, ib, strides)

    # Write ini file
    if operator.generate_ini_file:
        # FIXME: Still want to write out the ini file without a pixel shader
        # hash. It's only the ShaderOverride that is affected by that
        if obj['3DMigoto:PSHash']:
            write_ini_file(open(ini_path, 'w'), vb, vb_path, ib, ib_path, strides, obj, orig_topology, operator.override_vertex_shader, operator.texture_override_range)
        else:
            operator.report({'WARNING'}, 'ini file will NOT be generated. The hashes were not found on the currently selected object name.')

semantic_remap_enum = [
        ('None', 'No change', 'Do not remap this semantic. If the semantic name is recognised the script will try to interpret it, otherwise it will preserve the existing data in a vertex layer'),
        ('POSITION', 'POSITION', 'This data will be used as the vertex positions. There should generally be exactly one POSITION semantic for hopefully obvious reasons'),
        ('NORMAL', 'NORMAL', 'This data will be used as split (custom) normals in Blender.'),
        ('TANGENT', 'TANGENT (CAUTION: Discards data!)', 'Data in the TANGENT semantics are discarded on import, and recalculated on export'),
        #('BINORMAL', 'BINORMAL', "Don't encourage anyone to choose this since the data will be entirely discarded"),
        ('BLENDINDICES', 'BLENDINDICES', 'This semantic holds the vertex group indices, and should be paired with a BLENDWEIGHT semantic that has the corresponding weights for these groups'),
        ('BLENDWEIGHT', 'BLENDWEIGHT', 'This semantic holds the vertex group weights, and should be paired with a BLENDINDICES semantic that has the corresponding vertex group indices that these weights apply to'),
        ('TEXCOORD', 'TEXCOORD', 'Typically holds UV coordinates, though can also be custom data. Choosing this will import the data as a UV layer (or two) in Blender'),
        ('COLOR', 'COLOR', 'Typically used for vertex colors, though can also be custom data. Choosing this option will import the data as a vertex color layer in Blender'),
        ('Preserve', 'Unknown / Preserve', "Don't try to interpret the data. Choosing this option will simply store the data in a vertex layer in Blender so that it can later be exported unmodified"),
    ]

class FALogFile(object):
    '''
    Class that is able to parse frame analysis log files, query bound resource
    state at the time of a given draw call, and search for resource usage.

    TODO: Support hold frame analysis log files that include multiple frames
    TODO: Track bound shaders
    TODO: Merge deferred context log files into main log file
    TODO: Track CopyResource / other ways resources can be updated
    '''
    ResourceUse = collections.namedtuple('ResourceUse', ['draw_call', 'slot_type', 'slot'])
    class SparseSlots(dict):
        '''
        Allows the resources bound in each slot to be stored + queried by draw
        call. There can be gaps with draw calls that don't change any of the
        given slot type, in which case it will return the slots in the most
        recent draw call that did change that slot type.

        Requesting a draw call higher than any seen so far will return a *copy*
        of the most recent slots, intended for modification during parsing.
        '''
        def __init__(self):
            dict.__init__(self, {0: {}})
            self.last_draw_call = 0
        def prev_draw_call(self, draw_call):
            return max([ i for i in self.keys() if i < draw_call ])
        #def next_draw_call(self, draw_call):
        #    return min([ i for i in self.keys() if i > draw_call ])
        def subsequent_draw_calls(self, draw_call):
            return [ i for i in sorted(self.keys()) if i >= draw_call ]
        def __getitem__(self, draw_call):
            if draw_call > self.last_draw_call:
                dict.__setitem__(self, draw_call, dict.__getitem__(self, self.last_draw_call).copy())
                self.last_draw_call = draw_call
            elif draw_call not in self.keys():
                return dict.__getitem__(self, self.prev_draw_call(draw_call))
            return dict.__getitem__(self, draw_call)

    class FALogParser(object):
        '''
        Base class implementing some common parsing functions
        '''
        pattern = None
        def parse(self, line, q, state):
            match = self.pattern.match(line)
            if match:
                remain = line[match.end():]
                self.matched(match, remain, q, state)
            return match
        def matched(self, match, remain, q, state):
            raise NotImplemented()

    class FALogParserDrawcall(FALogParser):
        '''
        Parses a typical line in a frame analysis log file that begins with a
        draw call number. Additional parsers can be registered with this one to
        parse the remainder of such lines.
        '''
        pattern = re.compile(r'''^(?P<drawcall>\d+) ''')
        next_parsers_classes = []
        @classmethod
        def register(cls, parser):
            cls.next_parsers_classes.append(parser)
        def __init__(self, state):
            self.next_parsers = []
            for parser in self.next_parsers_classes:
                self.next_parsers.append(parser(state))
        def matched(self, match, remain, q, state):
            drawcall = int(match.group('drawcall'))
            state.draw_call = drawcall
            for parser in self.next_parsers:
                parser.parse(remain, q, state)

    class FALogParserBindResources(FALogParser):
        '''
        Base class for any parsers that bind resources (and optionally views)
        to the pipeline. Will consume all following lines matching the resource
        pattern and update the log file state and resource lookup index for the
        current draw call.
        '''
        resource_pattern = re.compile(r'''^\s+(?P<slot>[0-9D]+): (?:view=(?P<view>0x[0-9A-F]+) )?resource=(?P<address>0x[0-9A-F]+) hash=(?P<hash>[0-9a-f]+)$''', re.MULTILINE)
        FALogResourceBinding = collections.namedtuple('FALogResourceBinding', ['slot', 'view_address', 'resource_address', 'resource_hash'])
        slot_prefix = None
        bind_clears_all_slots = False
        def __init__(self, state):
            if self.slot_prefix is None:
                raise NotImplemented()
            self.sparse_slots = FALogFile.SparseSlots()
            state.slot_class[self.slot_prefix] = self.sparse_slots
        def matched(self, api_match, remain, q, state):
            if self.bind_clears_all_slots:
                self.sparse_slots[state.draw_call].clear()
            else:
                start_slot = self.start_slot(api_match)
                for i in range(self.num_bindings(api_match)):
                    self.sparse_slots[state.draw_call].pop(start_slot + i, None)
            bindings = self.sparse_slots[state.draw_call]
            while self.resource_pattern.match(q[0]):
                # FIXME: Inefficiently calling match twice. I hate that Python
                # lacks a do/while and every workaround is ugly in some way.
                resource_match = self.resource_pattern.match(q.popleft())
                slot = resource_match.group('slot')
                if slot.isnumeric(): slot = int(slot)
                view = resource_match.group('view')
                if view: view = int(view, 16)
                address = int(resource_match.group('address'), 16)
                resource_hash = int(resource_match.group('hash'), 16)
                bindings[slot] = self.FALogResourceBinding(slot, view, address, resource_hash)
                state.resource_index[address].add(FALogFile.ResourceUse(state.draw_call, self.slot_prefix, slot))
            #print(sorted(bindings.items()))
        def start_slot(self, match):
            return int(match.group('StartSlot'))
        def num_bindings(self, match):
            return int(match.group('NumBindings'))

    class FALogParserSOSetTargets(FALogParserBindResources):
        pattern = re.compile(r'''SOSetTargets\(.*\)$''')
        slot_prefix = 'so'
        bind_clears_all_slots = True
    FALogParserDrawcall.register(FALogParserSOSetTargets)

    class FALogParserIASetVertexBuffers(FALogParserBindResources):
        pattern = re.compile(r'''IASetVertexBuffers\(StartSlot:(?P<StartSlot>[0-9]+), NumBuffers:(?P<NumBindings>[0-9]+),.*\)$''')
        slot_prefix = 'vb'
    FALogParserDrawcall.register(FALogParserIASetVertexBuffers)

    # At the moment we don't need to track other pipeline slots, so to keep
    # things faster and use less memory we don't bother with slots we don't
    # need to know about. but if we wanted to the above makes it fairly trivial
    # to add additional slot classes, e.g. to track bound texture slots (SRVs)
    # for all shader types uncomment the following:
    #class FALogParserVSSetShaderResources(FALogParserBindResources):
    #    pattern = re.compile(r'''VSSetShaderResources\(StartSlot:(?P<StartSlot>[0-9]+), NumViews:(?P<NumBindings>[0-9]+),.*\)$''')
    #    slot_prefix = 'vs-t'
    #class FALogParserDSSetShaderResources(FALogParserBindResources):
    #    pattern = re.compile(r'''DSSetShaderResources\(StartSlot:(?P<StartSlot>[0-9]+), NumViews:(?P<NumBindings>[0-9]+),.*\)$''')
    #    slot_prefix = 'ds-t'
    #class FALogParserHSSetShaderResources(FALogParserBindResources):
    #    pattern = re.compile(r'''HSSetShaderResources\(StartSlot:(?P<StartSlot>[0-9]+), NumViews:(?P<NumBindings>[0-9]+),.*\)$''')
    #    slot_prefix = 'hs-t'
    #class FALogParserGSSetShaderResources(FALogParserBindResources):
    #    pattern = re.compile(r'''GSSetShaderResources\(StartSlot:(?P<StartSlot>[0-9]+), NumViews:(?P<NumBindings>[0-9]+),.*\)$''')
    #    slot_prefix = 'gs-t'
    #class FALogParserPSSetShaderResources(FALogParserBindResources):
    #    pattern = re.compile(r'''PSSetShaderResources\(StartSlot:(?P<StartSlot>[0-9]+), NumViews:(?P<NumBindings>[0-9]+),.*\)$''')
    #    slot_prefix = 'ps-t'
    #class FALogParserCSSetShaderResources(FALogParserBindResources):
    #    pattern = re.compile(r'''CSSetShaderResources\(StartSlot:(?P<StartSlot>[0-9]+), NumViews:(?P<NumBindings>[0-9]+),.*\)$''')
    #    slot_prefix = 'cs-t'
    #FALogParserDrawcall.register(FALogParserVSSetShaderResources)
    #FALogParserDrawcall.register(FALogParserDSSetShaderResources)
    #FALogParserDrawcall.register(FALogParserHSSetShaderResources)
    #FALogParserDrawcall.register(FALogParserGSSetShaderResources)
    #FALogParserDrawcall.register(FALogParserPSSetShaderResources)
    #FALogParserDrawcall.register(FALogParserCSSetShaderResources)

    # Uncomment these to track bound constant buffers:
    #class FALogParserVSSetConstantBuffers(FALogParserBindResources):
    #    pattern = re.compile(r'''VSSetConstantBuffers\(StartSlot:(?P<StartSlot>[0-9]+), NumBuffers:(?P<NumBindings>[0-9]+),.*\)$''')
    #    slot_prefix = 'vs-cb'
    #class FALogParserDSSetConstantBuffers(FALogParserBindResources):
    #    pattern = re.compile(r'''DSSetConstantBuffers\(StartSlot:(?P<StartSlot>[0-9]+), NumBuffers:(?P<NumBindings>[0-9]+),.*\)$''')
    #    slot_prefix = 'ds-cb'
    #class FALogParserHSSetConstantBuffers(FALogParserBindResources):
    #    pattern = re.compile(r'''HSSetConstantBuffers\(StartSlot:(?P<StartSlot>[0-9]+), NumBuffers:(?P<NumBindings>[0-9]+),.*\)$''')
    #    slot_prefix = 'hs-cb'
    #class FALogParserGSSetConstantBuffers(FALogParserBindResources):
    #    pattern = re.compile(r'''GSSetConstantBuffers\(StartSlot:(?P<StartSlot>[0-9]+), NumBuffers:(?P<NumBindings>[0-9]+),.*\)$''')
    #    slot_prefix = 'gs-cb'
    #class FALogParserPSSetConstantBuffers(FALogParserBindResources):
    #    pattern = re.compile(r'''PSSetConstantBuffers\(StartSlot:(?P<StartSlot>[0-9]+), NumBuffers:(?P<NumBindings>[0-9]+),.*\)$''')
    #    slot_prefix = 'ps-cb'
    #class FALogParserCSSetConstantBuffers(FALogParserBindResources):
    #    pattern = re.compile(r'''CSSetConstantBuffers\(StartSlot:(?P<StartSlot>[0-9]+), NumBuffers:(?P<NumBindings>[0-9]+),.*\)$''')
    #    slot_prefix = 'cs-cb'
    #FALogParserDrawcall.register(FALogParserVSSetConstantBuffers)
    #FALogParserDrawcall.register(FALogParserDSSetConstantBuffers)
    #FALogParserDrawcall.register(FALogParserHSSetConstantBuffers)
    #FALogParserDrawcall.register(FALogParserGSSetConstantBuffers)
    #FALogParserDrawcall.register(FALogParserPSSetConstantBuffers)
    #FALogParserDrawcall.register(FALogParserCSSetConstantBuffers)

    # Uncomment to tracks render targets (note that this doesn't yet take into
    # account games using OMSetRenderTargetsAndUnorderedAccessViews)
    #class FALogParserOMSetRenderTargets(FALogParserBindResources):
    #    pattern = re.compile(r'''OMSetRenderTargets\(NumViews:(?P<NumBindings>[0-9]+),.*\)$''')
    #    slot_prefix = 'o'
    #    bind_clears_all_slots = True
    #FALogParserDrawcall.register(FALogParserOMSetRenderTargets)

    def __init__(self, f):
        self.draw_call = None
        self.slot_class = {}
        self.resource_index = collections.defaultdict(set)
        draw_call_parser = self.FALogParserDrawcall(self)
        # Using a deque for a concise way to use a pop iterator and be able to
        # peek/consume the following line. Maybe overkill, but shorter code
        q = collections.deque(f)
        q.append(None)
        for line in iter(q.popleft, None):
            #print(line)
            if not draw_call_parser.parse(line, q, self):
                #print(line)
                pass

    def find_resource_uses(self, resource_address, slot_class=None):
        '''
        Find draw calls + slots where this resource is used.
        '''
        #return [ x for x in sorted(self.resource_index[resource_address]) if x.slot_type == slot_class ]
        ret = set()
        for bound in sorted(self.resource_index[resource_address]):
            if slot_class is not None and bound.slot_type != slot_class:
                continue
            # Resource was bound in this draw call, but could potentially have
            # been left bound in subsequent draw calls that we also want to
            # return, so return a range of draw calls if appropriate:
            sparse_slots = self.slot_class[bound.slot_type]
            for sparse_draw_call in sparse_slots.subsequent_draw_calls(bound.draw_call):
                if bound.slot not in sparse_slots[sparse_draw_call] \
                or sparse_slots[sparse_draw_call][bound.slot].resource_address != resource_address:
                    #print('x', sparse_draw_call, sparse_slots[sparse_draw_call][bound.slot])
                    for draw_call in range(bound.draw_call, sparse_draw_call):
                        ret.add(FALogFile.ResourceUse(draw_call, bound.slot_type, bound.slot))
                    break
                #print('y', sparse_draw_call, sparse_slots[sparse_draw_call][bound.slot])
            else:
                # I love Python's for/else clause. Means we didn't hit the
                # above break so the resource was still bound at end of frame
                for draw_call in range(bound.draw_call, self.draw_call):
                    ret.add(FALogFile.ResourceUse(draw_call, bound.slot_type, bound.slot))
        return ret

VBSOMapEntry = collections.namedtuple('VBSOMapEntry', ['draw_call', 'slot'])
def find_stream_output_vertex_buffers(log):
    vb_so_map = {}
    for so_draw_call, bindings in log.slot_class['so'].items():
        for so_slot, so in bindings.items():
            #print(so_draw_call, so_slot, so.resource_address)
            #print(list(sorted(log.find_resource_uses(so.resource_address, 'vb'))))
            for vb_draw_call, slot_type, vb_slot in log.find_resource_uses(so.resource_address, 'vb'):
                # NOTE: Recording the stream output slot here, but that won't
                # directly help determine which VB inputs we need from this
                # draw call (all of them, or just some?), but we might want
                # this slot if we write out an ini file for reinjection
                vb_so_map[VBSOMapEntry(vb_draw_call, vb_slot)] = VBSOMapEntry(so_draw_call, so_slot)
    #print(sorted(vb_so_map.items()))
    return vb_so_map

def open_frame_analysis_log_file(dirname):
    basename = os.path.basename(dirname)
    if basename.lower().startswith('ctx-0x'):
        context = basename[6:]
        path = os.path.join(dirname, '..', f'log-0x{context}.txt')
    else:
        path = os.path.join(dirname, 'log.txt')
    return FALogFile(open(path, 'r'))

class SemanticRemapItem(bpy.types.PropertyGroup):
    semantic_from: bpy.props.StringProperty(name="From", default="ATTRIBUTE")
    semantic_to:   bpy.props.EnumProperty(items=semantic_remap_enum, name="Change semantic interpretation")
    # Extra information when this is filled out automatically that might help guess the correct semantic:
    Format:            bpy.props.StringProperty(name="DXGI Format")
    InputSlot:         bpy.props.IntProperty(name="Vertex Buffer")
    InputSlotClass:    bpy.props.StringProperty(name="Input Slot Class")
    AlignedByteOffset: bpy.props.IntProperty(name="Aligned Byte Offset")
    valid:             bpy.props.BoolProperty(default=True)
    tooltip:           bpy.props.StringProperty(default="This is a manually added entry. It's recommended to pre-fill semantics from selected files via the menu to the right to avoid typos")
    def update_tooltip(self):
        if not self.Format:
            return
        self.tooltip = 'vb{}+{} {}'.format(self.InputSlot, self.AlignedByteOffset, self.Format)
        if self.InputSlotClass == 'per-instance':
            self.tooltip = '. This semantic holds per-instance data (such as per-object transformation matrices) which will not be used by the script'
        elif self.valid == False:
            self.tooltip += ". This semantic is invalid - it may share the same location as another semantic or the vertex buffer it belongs to may be missing / too small"

class MIGOTO_UL_semantic_remap_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "semantic_from", text="", emboss=False, icon_value=icon)
            if item.InputSlotClass == 'per-instance':
                layout.label(text="Instanced Data")
                layout.enabled = False
            elif item.valid == False:
                layout.label(text="INVALID")
                layout.enabled = False
            else:
                layout.prop(item, "semantic_to", text="", emboss=False, icon_value=icon)
        elif self.layout_type == 'GRID':
            # Doco says we must implement this layout type, but I don't see
            # that it would be particularly useful, and not sure if we actually
            # expect the list to render with this type in practice. Untested.
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

class MIGOTO_MT_semantic_remap_menu(bpy.types.Menu):
    bl_label = "Semantic Remap Options"

    def draw(self, context):
        layout = self.layout

        layout.operator(ClearSemanticRemapList.bl_idname)
        layout.operator(PrefillSemanticRemapList.bl_idname)

class ClearSemanticRemapList(bpy.types.Operator):
    """Clear the semantic remap list"""
    bl_idname = "import_mesh.migoto_semantic_remap_clear"
    bl_label = "Clear list"

    def execute(self, context):
        import_operator = context.space_data.active_operator
        import_operator.properties.semantic_remap.clear()
        return {'FINISHED'}

class PrefillSemanticRemapList(bpy.types.Operator):
    """Add semantics from the selected files to the semantic remap list"""
    bl_idname = "import_mesh.migoto_semantic_remap_prefill"
    bl_label = "Prefill from selected files"

    def execute(self, context):
        import_operator = context.space_data.active_operator
        semantic_remap_list = import_operator.properties.semantic_remap
        semantics_in_list = { x.semantic_from for x in semantic_remap_list }

        paths = import_operator.get_vb_ib_paths(load_related=False)

        for p in paths:
            vb, ib, name, pose_path = load_3dmigoto_mesh(import_operator, [p])
            valid_semantics = vb.get_valid_semantics()
            for semantic in vb.layout:
                if semantic.name not in semantics_in_list:
                    remap = semantic_remap_list.add()
                    remap.semantic_from = semantic.name
                    # Store some extra information that can be helpful to guess the likely semantic:
                    remap.Format = semantic.Format
                    remap.InputSlot = semantic.InputSlot
                    remap.InputSlotClass = semantic.InputSlotClass
                    remap.AlignedByteOffset = semantic.AlignedByteOffset
                    remap.valid = semantic.name in valid_semantics
                    remap.update_tooltip()
                    semantics_in_list.add(semantic.name)

        return {'FINISHED'}

@orientation_helper(axis_forward='-Z', axis_up='Y')
class Import3DMigotoFrameAnalysis(bpy.types.Operator, ImportHelper, IOOBJOrientationHelper):
    """Import a mesh dumped with 3DMigoto's frame analysis"""
    bl_idname = "import_mesh.migoto_frame_analysis"
    bl_label = "Import 3DMigoto Frame Analysis Dump"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = '.txt'
    filter_glob: StringProperty(
            default='*.txt',
            options={'HIDDEN'},
            )

    files: CollectionProperty(
            name="File Path",
            type=bpy.types.OperatorFileListElement,
            )

    flip_texcoord_v: BoolProperty(
            name="Flip TEXCOORD V",
            description="Flip TEXCOORD V asix during importing",
            default=True,
            )

    flip_winding: BoolProperty(
            name="Flip Winding Order",
            description="Flip winding order (face orientation) during importing. Try if the model doesn't seem to be shading as expected in Blender and enabling the 'Face Orientation' overlay shows **RED** (if it shows BLUE, try 'Flip Normal' instead). Not quite the same as flipping normals within Blender as this only reverses the winding order without flipping the normals. Recommended for Unreal Engine",
            default=False,
            )

    flip_normal: BoolProperty(
            name="Flip Normal",
            description="Flip Normals during importing. Try if the model doesn't seem to be shading as expected in Blender and enabling 'Face Orientation' overlay shows **BLUE** (if it shows RED, try 'Flip Winding Order' instead). Not quite the same as flipping normals within Blender as this won't reverse the winding order",
            default=False,
            )

    load_related: BoolProperty(
            name="Auto-load related meshes",
            description="Automatically load related meshes found in the frame analysis dump",
            default=True,
            )

    load_related_so_vb: BoolProperty(
            name="Load pre-SO buffers (EXPERIMENTAL)",
            description="Scans the frame analysis log file to find GPU pre-skinning Stream Output techniques in prior draw calls, and loads the unposed vertex buffers from those calls that are suitable for editing. Recommended for Unity games to load neutral poses",
            default=False,
            )

    load_buf: BoolProperty(
            name="Load .buf files instead",
            description="Load the mesh from the binary .buf dumps instead of the .txt files\nThis will load the entire mesh as a single object instead of separate objects from each draw call",
            default=False,
            )

    load_buf_limit_range: BoolProperty(
            name="Limit to draw range",
            description="Load just the vertices/indices used in the draw call (equivalent to loading the .txt files) instead of the complete buffer",
            default=False,
            )

    merge_meshes: BoolProperty(
            name="Merge meshes together",
            description="Merge all selected meshes together into one object. Meshes must be related",
            default=False,
            )

    pose_cb: StringProperty(
            name="Bone CB",
            description='Indicate a constant buffer slot (e.g. "vs-cb2") containing the bone matrices',
            default="",
            )

    pose_cb_off: bpy.props.IntVectorProperty(
            name="Bone CB range",
            description='Indicate start and end offsets (in multiples of 4 component values) to find the matrices in the Bone CB',
            default=[0,0],
            size=2,
            min=0,
            )

    pose_cb_step: bpy.props.IntProperty(
            name="Vertex group step",
            description='If used vertex groups are 0,1,2,3,etc specify 1. If they are 0,3,6,9,12,etc specify 3',
            default=1,
            min=1,
            )

    semantic_remap: bpy.props.CollectionProperty(type=SemanticRemapItem)
    semantic_remap_idx: bpy.props.IntProperty(
            name='Semantic Remap',
            description='Enter the SemanticName and SemanticIndex the game is using on the left (e.g. TEXCOORD3), and what type of semantic the script should treat it as on the right') # Needed for template_list

    def get_vb_ib_paths(self, load_related=None):
        buffer_pattern = re.compile(r'''-(?:ib|vb[0-9]+)(?P<hash>=[0-9a-f]+)?(?=[^0-9a-f=])''')
        vb_regex = re.compile(r'''^(?P<draw_call>[0-9]+)-vb(?P<slot>[0-9]+)=''') # TODO: Combine with above? (careful not to break hold type frame analysis)

        dirname = os.path.dirname(self.filepath)
        ret = set()
        if load_related is None:
            load_related = self.load_related

        vb_so_map = {}
        if self.load_related_so_vb:
            try:
                fa_log = open_frame_analysis_log_file(dirname)
            except FileNotFoundError:
                self.report({'WARNING'}, 'Frame Analysis Log File not found, loading unposed meshes from GPU Stream Output pre-skinning passes will be unavailable')
            else:
                vb_so_map = find_stream_output_vertex_buffers(fa_log)

        files = set()
        if load_related:
            for filename in self.files:
                match = buffer_pattern.search(filename.name)
                if match is None or not match.group('hash'):
                    continue
                paths = glob(os.path.join(dirname, '*%s*.txt' % filename.name[match.start():match.end()]))
                files.update([os.path.basename(x) for x in paths])
        if not files:
            files = [x.name for x in self.files]
            if files == ['']:
                raise Fatal('No files selected')

        done = set()
        for filename in files:
            if filename in done:
                continue
            match = buffer_pattern.search(filename)
            if match is None:
                if filename.lower().startswith('log') or filename.lower() == 'shaderusage.txt':
                    # User probably just selected all files including the log
                    continue
                # TODO: Perhaps don't warn about extra files that may have been
                # dumped out that we aren't specifically importing (such as
                # constant buffers dumped with dump_cb or any buffer dumped
                # with dump=), maybe provided we are loading other files from
                # that draw call. Note that this is only applicable if 'load
                # related' is disabled, as that option effectively filters
                # these out above. For now just changed this to an error report
                # rather than a Fatal so other files will still get loaded.
                self.report({'ERROR'}, 'Unable to find corresponding buffers from "{}" - filename did not match vertex/index buffer pattern'.format(filename))
                continue

            use_bin = self.load_buf
            if not match.group('hash') and not use_bin:
                self.report({'INFO'}, 'Filename did not contain hash - if Frame Analysis dumped a custom resource the .txt file may be incomplete, Using .buf files instead')
                use_bin = True # FIXME: Ask

            ib_pattern = filename[:match.start()] + '-ib*' + filename[match.end():]
            vb_pattern = filename[:match.start()] + '-vb*' + filename[match.end():]
            ib_paths = glob(os.path.join(dirname, ib_pattern))
            vb_paths = glob(os.path.join(dirname, vb_pattern))
            done.update(map(os.path.basename, itertools.chain(vb_paths, ib_paths)))

            if vb_so_map:
                vb_so_paths = set()
                for vb_path in vb_paths:
                    vb_match = vb_regex.match(os.path.basename(vb_path))
                    if vb_match:
                        draw_call, slot = map(int, vb_match.group('draw_call', 'slot'))
                        so = vb_so_map.get(VBSOMapEntry(draw_call, slot))
                        if so:
                            # No particularly good way to determine which input
                            # vertex buffers we need from the stream-output
                            # pass, so for now add them all:
                            vb_so_pattern = f'{so.draw_call:06}-vb*.txt'
                            glob_result = glob(os.path.join(dirname, vb_so_pattern))
                            if not glob_result:
                                self.report({'WARNING'}, f'{vb_so_pattern} not found, loading unposed meshes from GPU Stream Output pre-skinning passes will be unavailable')
                            vb_so_paths.update(glob_result)
                # FIXME: Not sure yet whether the extra vertex buffers from the
                # stream output pre-skinning passes are best lumped in with the
                # existing vb_paths or added as a separate set of paths. Advantages
                # + disadvantages to each, and either way will need work.
                vb_paths.extend(sorted(vb_so_paths))

            if vb_paths and use_bin:
                vb_bin_paths = [ os.path.splitext(x)[0] + '.buf' for x in vb_paths ]
                ib_bin_paths = [ os.path.splitext(x)[0] + '.buf' for x in ib_paths ]
                if all([ os.path.exists(x) for x in itertools.chain(vb_bin_paths, ib_bin_paths) ]):
                    # When loading the binary files, we still need to process
                    # the .txt files as well, as they indicate the format:
                    ib_paths = list(zip(ib_bin_paths, ib_paths))
                    vb_paths = list(zip(vb_bin_paths, vb_paths))
                else:
                    self.report({'WARNING'}, 'Corresponding .buf files not found - using .txt files')
                    use_bin = False

            pose_path = None
            if self.pose_cb:
                pose_pattern = filename[:match.start()] + '*-' + self.pose_cb + '=*.txt'
                try:
                    pose_path = glob(os.path.join(dirname, pose_pattern))[0]
                except IndexError:
                    pass

            if len(ib_paths) > 1:
                raise Fatal('Error: excess index buffers in dump?')
            elif len(ib_paths) == 0:
                if use_bin:
                    name = os.path.basename(vb_paths[0][0])
                    ib_paths = [(None, None)]
                else:
                    name = os.path.basename(vb_paths[0])
                    ib_paths = [None]
                self.report({'WARNING'}, '{}: No index buffer present, support for this case is highly experimental'.format(name))
            ret.add(ImportPaths(tuple(vb_paths), ib_paths[0], use_bin, pose_path))
        return ret

    def execute(self, context):
        if self.load_buf:
            # Is there a way to have the mutual exclusivity reflected in
            # the UI? Grey out options or use radio buttons or whatever?
            if self.merge_meshes or self.load_related:
                self.report({'INFO'}, 'Loading .buf files selected: Disabled incompatible options')
            self.merge_meshes = False
            self.load_related = False

        try:
            keywords = self.as_keywords(ignore=('filepath', 'files',
                'filter_glob', 'load_related', 'load_related_so_vb',
                'load_buf', 'pose_cb', 'load_buf_limit_range',
                'semantic_remap', 'semantic_remap_idx'))
            paths = self.get_vb_ib_paths()

            import_3dmigoto(self, context, paths, **keywords)
        except Fatal as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}

    def draw(self, context):
        # Overriding the draw method to disable automatically adding operator
        # properties to options panel, so we can define sub-panels to group
        # options and disable grey out mutually exclusive options.
        pass

class MigotoImportOptionsPanelBase(object):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        operator = context.space_data.active_operator
        return operator.bl_idname == "IMPORT_MESH_OT_migoto_frame_analysis"

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

class MIGOTO_PT_ImportFrameAnalysisMainPanel(MigotoImportOptionsPanelBase, bpy.types.Panel):
    bl_label = ""
    bl_options = {'HIDE_HEADER'}

    def draw(self, context):
        MigotoImportOptionsPanelBase.draw(self, context)
        operator = context.space_data.active_operator
        self.layout.prop(operator, "flip_texcoord_v")
        self.layout.prop(operator, "flip_winding")
        self.layout.prop(operator, "flip_normal")

class MIGOTO_PT_ImportFrameAnalysisRelatedFilesPanel(MigotoImportOptionsPanelBase, bpy.types.Panel):
    bl_label = ""
    bl_options = {'HIDE_HEADER'}

    def draw(self, context):
        MigotoImportOptionsPanelBase.draw(self, context)
        operator = context.space_data.active_operator
        self.layout.enabled = not operator.load_buf
        self.layout.prop(operator, "load_related")
        #self.layout.prop(operator, "load_related_so_vb")
        self.layout.prop(operator, "merge_meshes")

class MIGOTO_PT_ImportFrameAnalysisBufFilesPanel(MigotoImportOptionsPanelBase, bpy.types.Panel):
    bl_label = "Load .buf files instead"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        operator = context.space_data.active_operator
        self.layout.prop(operator, "load_buf", text="")

    def draw(self, context):
        MigotoImportOptionsPanelBase.draw(self, context)
        operator = context.space_data.active_operator
        self.layout.enabled = operator.load_buf
        self.layout.prop(operator, "load_buf_limit_range")

class MIGOTO_PT_ImportFrameAnalysisBonePanel(MigotoImportOptionsPanelBase, bpy.types.Panel):
    bl_label = ""
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        operator = context.space_data.active_operator
        self.layout.prop(operator, "pose_cb")

    def draw(self, context):
        MigotoImportOptionsPanelBase.draw(self, context)
        operator = context.space_data.active_operator
        self.layout.prop(operator, "pose_cb_off")
        self.layout.prop(operator, "pose_cb_step")

class MIGOTO_PT_ImportFrameAnalysisRemapSemanticsPanel(MigotoImportOptionsPanelBase, bpy.types.Panel):
    bl_label = "Semantic Remap"
    #bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        MigotoImportOptionsPanelBase.draw(self, context)
        operator = context.space_data.active_operator

        # TODO: Add layout.operator() to read selected file and fill in semantics

        if context.path_resolve is None:
            # Avoid exceptions in console - seems like draw() is called several
            # times (not sure why) and sometimes path_resolve isn't available.
            return
        if draw_ui_list is None:
            self.layout.label(text='Please update Blender to use this feature')
            return
        draw_ui_list(self.layout, context,
                class_name='MIGOTO_UL_semantic_remap_list',
                menu_class_name='MIGOTO_MT_semantic_remap_menu',
                list_path='active_operator.properties.semantic_remap',
                active_index_path='active_operator.properties.semantic_remap_idx',
                unique_id='migoto_import_semantic_remap_list',
                item_dyntip_propname='tooltip',
                )

class MIGOTO_PT_ImportFrameAnalysisManualOrientation(MigotoImportOptionsPanelBase, bpy.types.Panel):
    bl_label = "Orientation"

    def draw(self, context):
        MigotoImportOptionsPanelBase.draw(self, context)
        operator = context.space_data.active_operator
        self.layout.prop(operator, "axis_forward")
        self.layout.prop(operator, "axis_up")

def import_3dmigoto_raw_buffers(operator, context, vb_fmt_path, ib_fmt_path, vb_path=None, ib_path=None, vgmap_path=None, **kwargs):
    paths = (ImportPaths(vb_paths=list(zip(vb_path, [vb_fmt_path]*len(vb_path))), ib_paths=(ib_path, ib_fmt_path), use_bin=True, pose_path=None),)
    obj = import_3dmigoto(operator, context, paths, merge_meshes=False, **kwargs)
    if obj and vgmap_path:
        apply_vgmap(operator, context, targets=obj, filepath=vgmap_path, rename=True, cleanup=True)

@orientation_helper(axis_forward='-Z', axis_up='Y')
class Import3DMigotoRaw(bpy.types.Operator, ImportHelper, IOOBJOrientationHelper):
    """Import raw 3DMigoto vertex and index buffers"""
    bl_idname = "import_mesh.migoto_raw_buffers"
    bl_label = "Import 3DMigoto Raw Buffers"
    #bl_options = {'PRESET', 'UNDO'}
    bl_options = {'UNDO'}

    filename_ext = '.vb;.ib'
    filter_glob: StringProperty(
            default='*.vb*;*.ib',
            options={'HIDDEN'},
            )

    files: CollectionProperty(
            name="File Path",
            type=bpy.types.OperatorFileListElement,
            )

    flip_texcoord_v: BoolProperty(
            name="Flip TEXCOORD V",
            description="Flip TEXCOORD V axis during importing",
            default=True,
            )

    flip_winding: BoolProperty(
            name="Flip Winding Order",
            description="Flip winding order (face orientation) during importing. Try if the model doesn't seem to be shading as expected in Blender and enabling the 'Face Orientation' overlay shows **RED** (if it shows BLUE, try 'Flip Normal' instead). Not quite the same as flipping normals within Blender as this only reverses the winding order without flipping the normals. Recommended for Unreal Engine",
            default=False,
            )

    flip_normal: BoolProperty(
            name="Flip Normal",
            description="Flip Normals during importing. Try if the model doesn't seem to be shading as expected in Blender and enabling 'Face Orientation' overlay shows **BLUE** (if it shows RED, try 'Flip Winding Order' instead). Not quite the same as flipping normals within Blender as this won't reverse the winding order",
            default=False,
            )

    def get_vb_ib_paths(self, filename):
        vb_bin_path = glob(os.path.splitext(filename)[0] + '.vb*')
        ib_bin_path = os.path.splitext(filename)[0] + '.ib'
        fmt_path = os.path.splitext(filename)[0] + '.fmt'
        vgmap_path = os.path.splitext(filename)[0] + '.vgmap'
        if len(vb_bin_path) < 1:
            raise Fatal('Unable to find matching .vb* file(s) for %s' % filename)
        if not os.path.exists(ib_bin_path):
            ib_bin_path = None
        if not os.path.exists(fmt_path):
            fmt_path = None
        if not os.path.exists(vgmap_path):
            vgmap_path = None
        return (vb_bin_path, ib_bin_path, fmt_path, vgmap_path)

    def execute(self, context):
        # I'm not sure how to find the Import3DMigotoReferenceInputFormat
        # instance that Blender instantiated to pass the values from one
        # import dialog to another, but since everything is modal we can
        # just use globals:
        global migoto_raw_import_options
        migoto_raw_import_options = self.as_keywords(ignore=('filepath', 'files', 'filter_glob'))

        done = set()
        dirname = os.path.dirname(self.filepath)
        for filename in self.files:
            try:
                (vb_path, ib_path, fmt_path, vgmap_path) = self.get_vb_ib_paths(os.path.join(dirname, filename.name))
                vb_path_norm = set(map(os.path.normcase, vb_path))
                if vb_path_norm.intersection(done) != set():
                    continue
                done.update(vb_path_norm)

                if fmt_path is not None:
                    import_3dmigoto_raw_buffers(self, context, fmt_path, fmt_path, vb_path=vb_path, ib_path=ib_path, vgmap_path=vgmap_path, **migoto_raw_import_options)
                else:
                    migoto_raw_import_options['vb_path'] = vb_path
                    migoto_raw_import_options['ib_path'] = ib_path
                    bpy.ops.import_mesh.migoto_input_format('INVOKE_DEFAULT')
            except Fatal as e:
                self.report({'ERROR'}, str(e))
        return {'FINISHED'}

class Import3DMigotoReferenceInputFormat(bpy.types.Operator, ImportHelper):
    bl_idname = "import_mesh.migoto_input_format"
    bl_label = "Select a .txt file with matching format"
    bl_options = {'UNDO', 'INTERNAL'}

    filename_ext = '.txt;.fmt'
    filter_glob: StringProperty(
            default='*.txt;*.fmt',
            options={'HIDDEN'},
            )

    def get_vb_ib_paths(self):
        if os.path.splitext(self.filepath)[1].lower() == '.fmt':
            return (self.filepath, self.filepath)

        buffer_pattern = re.compile(r'''-(?:ib|vb[0-9]+)(?P<hash>=[0-9a-f]+)?(?=[^0-9a-f=])''')

        dirname = os.path.dirname(self.filepath)
        filename = os.path.basename(self.filepath)

        match = buffer_pattern.search(filename)
        if match is None:
            raise Fatal('Reference .txt filename does not look like a 3DMigoto timestamped Frame Analysis Dump')
        ib_pattern = filename[:match.start()] + '-ib*' + filename[match.end():]
        vb_pattern = filename[:match.start()] + '-vb*' + filename[match.end():]
        ib_paths = glob(os.path.join(dirname, ib_pattern))
        vb_paths = glob(os.path.join(dirname, vb_pattern))
        if len(ib_paths) < 1 or len(vb_paths) < 1:
            raise Fatal('Unable to locate reference files for both vertex buffer and index buffer format descriptions')
        return (vb_paths[0], ib_paths[0])

    def execute(self, context):
        global migoto_raw_import_options

        try:
            vb_fmt_path, ib_fmt_path = self.get_vb_ib_paths()
            import_3dmigoto_raw_buffers(self, context, vb_fmt_path, ib_fmt_path, **migoto_raw_import_options)
        except Fatal as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}

class Export3DMigoto(bpy.types.Operator, ExportHelper):
    """Export a mesh for re-injection into a game with 3DMigoto"""
    bl_idname = "export_mesh.migoto"
    bl_label = "Export 3DMigoto Vertex & Index Buffers"

    filename_ext = '.vb0'
    filter_glob: StringProperty(
            default='*.vb*',
            options={'HIDDEN'},
            )

    flip_winding: BoolProperty(
            name="Flip Winding Order",
            description="Flip winding order during export (automatically set to match the import option)",
            default=False,
            )

    flip_normal: BoolProperty(
            name="Flip Normal",
            description="Flip Normals during export (automatically set to match the import option)",
            default=False,
            )

    flip_tangent: BoolProperty(
            name="Flip Tangent",
            description="Flip Tangents during export (automatically set to match the flip normals option)",
            default=False,
            )

    # FIXME: Order of these options doesn't currently make sense, but we will
    # probably want to switch to the separate panels like the FA import dialog
    # so we can group them... let's worry about that later when the options are
    # a bit more finalised.
    override_vertex_shader: BoolProperty(
            name="Override VertexShader Instead",
            description="If the mod did not work by overriding the pixel shader, override the vertex shader instead",
            default=False,
            )

    # FIXME: Should be piecemeal options
    # - Generate resource sections. Would we ever NOT want this? I'm somewhat
    #   inclined to always enable this, but if we do that the filename needs to
    #   not be something the modder might have already created to avoid
    #   overwriting their work (we may want to do that anyway - I don't want an
    #   modder losing work if they wondered what this new checkbox does)
    # - Trivial override draw call (i.e. TextureOverride, description should
    #   mention situations where this is not suitable to include, like
    #   transparency overrides, exporting a body after swapping vertex groups
    #   from another mod, etc)
    # - ShaderOverride section (controversial, discussed elsewhere)
    #   - Path to central ShaderOverrides folder (if we end up going down that path)
    #   - What to write to the ShaderOverride section?
    #     - checktextureoverride=vb0 "just works", but is not recommended
    #     - run=CommandList... is strongly preferred, but requires base mod to be set up correctly
    generate_ini_file: BoolProperty(
            name="Generate Mod .ini",
            description="Your mod must be exported into a folder MyMod inside your Mods folder",
            default=False,
            )

    # FIXME: Too much risk of introducing subtle mod conflicts
    # FIXME: Belongs in the base mod command lists, not here
    # FIXME: Should allow no slots to be selected when they are unwanted (0 will enable ps-t0, not none)
    # FIXME: Technically should be a sparse list (but probably not a big deal)
    # FIXME: Description is unclear
    texture_override_range: bpy.props.IntProperty(
            name="Texture Range",
            description="Number [0-128] of ps-t textures to mod. Game-specific limit.",
            default=4,
            min=0,
            max=128
            )

    def invoke(self, context, event):
        obj = context.object
        self.flip_winding = obj.get('3DMigoto:FlipWinding', False)
        self.flip_tangent = self.flip_normal = obj.get('3DMigoto:FlipNormal', False)
        return ExportHelper.invoke(self, context, event)

    def execute(self, context):
        try:
            #Set paths
            vb_path = os.path.splitext(self.filepath)[0] + '.vb'
            ib_path = os.path.splitext(vb_path)[0] + '.ib'
            fmt_path = os.path.splitext(vb_path)[0] + '.fmt'
            # FIXME (or at least needs final decision): I don't think it's a
            # good idea to write an ini file with this name - there is just too
            # much risk that it will end up overwriting a modders work - too
            # many cases already exist in the wild using this filename.
            ini_path = os.path.splitext(vb_path)[0] + '.ini'

            # FIXME: ExportHelper will check for overwriting vb_path, but not ib_path

            export_3dmigoto(self, context, vb_path, ib_path, fmt_path, ini_path)
        except Fatal as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}

def apply_vgmap(operator, context, targets=None, filepath='', commit=False, reverse=False, suffix='', rename=False, cleanup=False):
    if not targets:
        targets = context.selected_objects

    if not targets:
        raise Fatal('No object selected')

    vgmap = json.load(open(filepath, 'r'))

    if reverse:
        vgmap = {int(v):int(k) for k,v in vgmap.items()}
    else:
        vgmap = {k:int(v) for k,v in vgmap.items()}

    for obj in targets:
        if commit:
            raise Fatal('commit not yet implemented')

        prop_name = '3DMigoto:VGMap:' + suffix
        obj[prop_name] = keys_to_strings(vgmap)

        if rename:
            for k,v in vgmap.items():
                if str(k) in obj.vertex_groups.keys():
                    continue
                if str(v) in obj.vertex_groups.keys():
                    obj.vertex_groups[str(v)].name = k
                else:
                    obj.vertex_groups.new(name=str(k))
        if cleanup:
            for vg in obj.vertex_groups:
                if vg.name not in vgmap:
                    obj.vertex_groups.remove(vg)

        if '3DMigoto:VBLayout' not in obj:
            operator.report({'WARNING'}, '%s is not a 3DMigoto mesh. Vertex Group Map custom property applied anyway' % obj.name)
        else:
            operator.report({'INFO'}, 'Applied vgmap to %s' % obj.name)

def update_vgmap(operator, context, vg_step=1):
    if not context.selected_objects:
        raise Fatal('No object selected')

    for obj in context.selected_objects:
        vgmaps = {k:keys_to_ints(v) for k,v in obj.items() if k.startswith('3DMigoto:VGMap:')}
        if not vgmaps:
            raise Fatal('Selected object has no 3DMigoto vertex group maps')
        for (suffix, vgmap) in vgmaps.items():
            highest = max(vgmap.values())
            for vg in obj.vertex_groups.keys():
                if vg.isdecimal():
                    continue
                if vg in vgmap:
                    continue
                highest += vg_step
                vgmap[vg] = highest
                operator.report({'INFO'}, 'Assigned named vertex group %s = %i' % (vg, vgmap[vg]))
            obj[suffix] = vgmap

class ApplyVGMap(bpy.types.Operator, ImportHelper):
    """Apply vertex group map to the selected object"""
    bl_idname = "mesh.migoto_vertex_group_map"
    bl_label = "Apply 3DMigoto vgmap"
    bl_options = {'UNDO'}

    filename_ext = '.vgmap'
    filter_glob: StringProperty(
            default='*.vgmap',
            options={'HIDDEN'},
            )

    #commit: BoolProperty(
    #        name="Commit to current mesh",
    #        description="Directly alters the vertex groups of the current mesh, rather than performing the mapping at export time",
    #        default=False,
    #        )

    rename: BoolProperty(
            name="Rename existing vertex groups",
            description="Rename existing vertex groups to match the vgmap file",
            default=True,
            )

    cleanup: BoolProperty(
            name="Remove non-listed vertex groups",
            description="Remove any existing vertex groups that are not listed in the vgmap file",
            default=False,
            )

    reverse: BoolProperty(
            name="Swap from & to",
            description="Switch the order of the vertex group map - if this mesh is the 'to' and you want to use the bones in the 'from'",
            default=False,
            )

    suffix: StringProperty(
            name="Suffix",
            description="Suffix to add to the vertex buffer filename when exporting, for bulk exports of a single mesh with multiple distinct vertex group maps",
            default='',
            )

    def invoke(self, context, event):
        self.suffix = ''
        return ImportHelper.invoke(self, context, event)

    def execute(self, context):
        try:
            keywords = self.as_keywords(ignore=('filter_glob',))
            apply_vgmap(self, context, **keywords)
        except Fatal as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}

class UpdateVGMap(bpy.types.Operator):
    """Assign new 3DMigoto vertex groups"""
    bl_idname = "mesh.update_migoto_vertex_group_map"
    bl_label = "Assign new 3DMigoto vertex groups"
    bl_options = {'UNDO'}

    vg_step: bpy.props.IntProperty(
            name="Vertex group step",
            description='If used vertex groups are 0,1,2,3,etc specify 1. If they are 0,3,6,9,12,etc specify 3',
            default=1,
            min=1,
            )

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        try:
            keywords = self.as_keywords()
            update_vgmap(self, context, **keywords)
        except Fatal as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}

class ConstantBuffer(object):
    def __init__(self, f, start_idx, end_idx):
        self.entries = []
        entry = []
        i = 0
        for line in map(str.strip, f):
            if line.startswith('buf') or line.startswith('cb'):
                entry.append(float(line.split()[1]))
                if len(entry) == 4:
                    if i >= start_idx:
                        self.entries.append(entry)
                    else:
                        print('Skipping', entry)
                    entry = []
                    i += 1
                    if end_idx and i > end_idx:
                        break
        assert(entry == [])

    def as_3x4_matrices(self):
        return [ Matrix(self.entries[i:i+3]) for i in range(0, len(self.entries), 3) ]

def import_pose(operator, context, filepath=None, limit_bones_to_vertex_groups=True, axis_forward='-Z', axis_up='Y', pose_cb_off=[0,0], pose_cb_step=1):
    pose_buffer = ConstantBuffer(open(filepath, 'r'), *pose_cb_off)

    matrices = pose_buffer.as_3x4_matrices()

    obj = context.object
    if not context.selected_objects:
        obj = None

    if limit_bones_to_vertex_groups and obj:
        matrices = matrices[:len(obj.vertex_groups)]

    name = os.path.basename(filepath)
    arm_data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, object_data=arm_data)

    conversion_matrix = axis_conversion(from_forward=axis_forward, from_up=axis_up).to_4x4()

    link_object_to_scene(context, arm)

    # Construct bones (FIXME: Position these better)
    # Must be in edit mode to add new bones
    select_set(arm, True)
    set_active_object(context, arm)
    bpy.ops.object.mode_set(mode='EDIT')
    for i, matrix in enumerate(matrices):
        bone = arm_data.edit_bones.new(str(i * pose_cb_step))
        bone.tail = Vector((0.0, 0.10, 0.0))
    bpy.ops.object.mode_set(mode='OBJECT')

    # Set pose:
    for i, matrix in enumerate(matrices):
        bone = arm.pose.bones[str(i * pose_cb_step)]
        matrix.resize_4x4()
        bone.matrix_basis = matmul(matmul(conversion_matrix, matrix), conversion_matrix.inverted())

    # Apply pose to selected object, if any:
    if obj is not None:
        mod = obj.modifiers.new(arm.name, 'ARMATURE')
        mod.object = arm
        obj.parent = arm
        # Hide pose object if it was applied to another object:
        hide_set(arm, True)

@orientation_helper(axis_forward='-Z', axis_up='Y')
class Import3DMigotoPose(bpy.types.Operator, ImportHelper, IOOBJOrientationHelper):
    """Import a pose from a 3DMigoto constant buffer dump"""
    bl_idname = "armature.migoto_pose"
    bl_label = "Import 3DMigoto Pose"
    bl_options = {'UNDO'}

    filename_ext = '.txt'
    filter_glob: StringProperty(
            default='*.txt',
            options={'HIDDEN'},
            )

    limit_bones_to_vertex_groups: BoolProperty(
            name="Limit Bones to Vertex Groups",
            description="Limits the maximum number of bones imported to the number of vertex groups of the active object",
            default=True,
            )

    pose_cb_off: bpy.props.IntVectorProperty(
            name="Bone CB range",
            description='Indicate start and end offsets (in multiples of 4 component values) to find the matrices in the Bone CB',
            default=[0,0],
            size=2,
            min=0,
            )

    pose_cb_step: bpy.props.IntProperty(
            name="Vertex group step",
            description='If used vertex groups are 0,1,2,3,etc specify 1. If they are 0,3,6,9,12,etc specify 3',
            default=1,
            min=1,
            )

    def execute(self, context):
        try:
            keywords = self.as_keywords(ignore=('filter_glob',))
            import_pose(self, context, **keywords)
        except Fatal as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}

def find_armature(obj):
    if obj is None:
        return None
    if obj.type == 'ARMATURE':
        return obj
    return obj.find_armature()

def copy_bone_to_target_skeleton(context, target_arm, new_name, src_bone):
    is_hidden = hide_get(target_arm)
    is_selected = select_get(target_arm)
    prev_active = get_active_object(context)
    hide_set(target_arm, False)
    select_set(target_arm, True)
    set_active_object(context, target_arm)

    bpy.ops.object.mode_set(mode='EDIT')
    bone = target_arm.data.edit_bones.new(new_name)
    bone.tail = Vector((0.0, 0.10, 0.0))
    bpy.ops.object.mode_set(mode='OBJECT')

    bone = target_arm.pose.bones[new_name]
    bone.matrix_basis = src_bone.matrix_basis

    set_active_object(context, prev_active)
    select_set(target_arm, is_selected)
    hide_set(target_arm, is_hidden)

def merge_armatures(operator, context):
    target_arm = find_armature(context.object)
    if target_arm is None:
        raise Fatal('No active target armature')
    #print('target:', target_arm)

    for src_obj in context.selected_objects:
        src_arm = find_armature(src_obj)
        if src_arm is None or src_arm == target_arm:
            continue
        #print('src:', src_arm)

        # Create mapping between common bones:
        bone_map = {}
        for src_bone in src_arm.pose.bones:
            for dst_bone in target_arm.pose.bones:
                # Seems important to use matrix_basis - if using 'matrix'
                # and merging multiple objects together, the last inserted bone
                # still has the identity matrix when merging the next pose in
                if src_bone.matrix_basis == dst_bone.matrix_basis:
                    if src_bone.name in bone_map:
                        operator.report({'WARNING'}, 'Source bone %s.%s matched multiple bones in the destination: %s, %s' %
                                (src_arm.name, src_bone.name, bone_map[src_bone.name], dst_bone.name))
                    else:
                        bone_map[src_bone.name] = dst_bone.name

        # Can't have a duplicate name, even temporarily, so rename all the
        # vertex groups first, and rename the source pose bones to match:
        orig_names = {}
        for vg in src_obj.vertex_groups:
            orig_name = vg.name
            vg.name = '%s.%s' % (src_arm.name, vg.name)
            orig_names[vg.name] = orig_name

        # Reassign vertex groups to matching bones in target armature:
        for vg in src_obj.vertex_groups:
            orig_name = orig_names[vg.name]
            if orig_name in bone_map:
                print('%s.%s -> %s' % (src_arm.name, orig_name, bone_map[orig_name]))
                vg.name = bone_map[orig_name]
            elif orig_name in src_arm.pose.bones:
                # FIXME: Make optional
                print('%s.%s -> new %s' % (src_arm.name, orig_name, vg.name))
                copy_bone_to_target_skeleton(context, target_arm, vg.name, src_arm.pose.bones[orig_name])
            else:
                print('Vertex group %s missing corresponding bone in %s' % (orig_name, src_arm.name))

        # Change existing armature modifier to target:
        for modifier in src_obj.modifiers:
            if modifier.type == 'ARMATURE' and modifier.object == src_arm:
                modifier.object = target_arm
        src_obj.parent = target_arm
        unlink_object(context, src_arm)

class Merge3DMigotoPose(bpy.types.Operator):
    """Merge identically posed bones of related armatures into one"""
    bl_idname = "armature.merge_pose"
    bl_label = "Merge 3DMigoto Poses"
    bl_options = {'UNDO'}

    def execute(self, context):
        try:
            merge_armatures(self, context)
        except Fatal as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}

class DeleteNonNumericVertexGroups(bpy.types.Operator):
    """Remove vertex groups with non-numeric names"""
    bl_idname = "vertex_groups.delete_non_numeric"
    bl_label = "Remove non-numeric vertex groups"
    bl_options = {'UNDO'}

    def execute(self, context):
        try:
            for obj in context.selected_objects:
                for vg in reversed(obj.vertex_groups):
                    if vg.name.isdecimal():
                        continue
                    print('Removing vertex group', vg.name)
                    obj.vertex_groups.remove(vg)
        except Fatal as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}

def menu_func_import_fa(self, context):
    self.layout.operator(Import3DMigotoFrameAnalysis.bl_idname, text="3DMigoto frame analysis dump (vb.txt + ib.txt)")

def menu_func_import_raw(self, context):
    self.layout.operator(Import3DMigotoRaw.bl_idname, text="3DMigoto raw buffers (.vb + .ib)")

def menu_func_import_pose(self, context):
    self.layout.operator(Import3DMigotoPose.bl_idname, text="3DMigoto pose (.txt)")

def menu_func_export(self, context):
    self.layout.operator(Export3DMigoto.bl_idname, text="3DMigoto raw buffers (.vb + .ib)")

def menu_func_apply_vgmap(self, context):
    self.layout.operator(ApplyVGMap.bl_idname, text="Apply 3DMigoto vertex group map to current object (.vgmap)")

register_classes = (
    SemanticRemapItem,
    MIGOTO_UL_semantic_remap_list,
    MIGOTO_MT_semantic_remap_menu,
    ClearSemanticRemapList,
    PrefillSemanticRemapList,
    Import3DMigotoFrameAnalysis,
    MIGOTO_PT_ImportFrameAnalysisMainPanel,
    MIGOTO_PT_ImportFrameAnalysisRelatedFilesPanel,
    MIGOTO_PT_ImportFrameAnalysisBufFilesPanel,
    MIGOTO_PT_ImportFrameAnalysisBonePanel,
    MIGOTO_PT_ImportFrameAnalysisRemapSemanticsPanel,
    MIGOTO_PT_ImportFrameAnalysisManualOrientation,
    Import3DMigotoRaw,
    Import3DMigotoReferenceInputFormat,
    Export3DMigoto,
    ApplyVGMap,
    UpdateVGMap,
    Import3DMigotoPose,
    Merge3DMigotoPose,
    DeleteNonNumericVertexGroups,
)

def register():
    for cls in register_classes:
        make_annotations(cls)
        bpy.utils.register_class(cls)

    import_menu.append(menu_func_import_fa)
    import_menu.append(menu_func_import_raw)
    export_menu.append(menu_func_export)
    import_menu.append(menu_func_apply_vgmap)
    import_menu.append(menu_func_import_pose)

def unregister():
    for cls in reversed(register_classes):
        bpy.utils.unregister_class(cls)

    import_menu.remove(menu_func_import_fa)
    import_menu.remove(menu_func_import_raw)
    export_menu.remove(menu_func_export)
    import_menu.remove(menu_func_apply_vgmap)
    import_menu.remove(menu_func_import_pose)

if __name__ == "__main__":
    register()
