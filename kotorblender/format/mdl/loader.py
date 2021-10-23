# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import os

from ...defines import Nodetype
from ...exception.malformedmdl import MalformedMdl
from ...exception.mdxnotfound import MdxNotFound
from ...scene.model import Model
from ...scene.modelnode import ModelNode
from ...scene.types import FaceList

from ..binreader import BinaryReader

MDL_OFFSET = 12

FN_PTR_1_K1_PC = 4273776
FN_PTR_1_K1_XBOX = 4254992
FN_PTR_1_K2_PC = 4285200
FN_PTR_1_K2_XBOX = 4285872
FN_PTR_2_K1_PC = 4216096
FN_PTR_2_K1_XBOX = 4255008
FN_PTR_2_K2_PC = 4216320
FN_PTR_2_K2_XBOX = 4216016

NODE_BASE = 0x0001
NODE_LIGHT = 0x0002
NODE_EMITTER = 0x0004
NODE_REFERENCE = 0x0010
NODE_MESH = 0x0020
NODE_SKIN = 0x0040
NODE_DANGLY = 0x0100
NODE_AABB = 0x0200
NODE_SABER = 0x0800

CTRL_BASE_POSITION = 8
CTRL_BASE_ORIENTATION = 20
CTRL_BASE_SCALE = 36

CTRL_MESH_SELFILLUMCOLOR = 100
CTRL_MESH_ALPHA = 132

CTRL_LIGHT_COLOR = 76
CTRL_LIGHT_RADIUS = 88
CTRL_LIGHT_SHADOWRADIUS = 96
CTRL_LIGHT_VERTICALDISPLACEMENT = 100
CTRL_LIGHT_MULTIPLIER = 140


class ControllerKey:
    def __init__(self, ctrl_type, num_rows, timekeys_start, values_start, num_columns):
        self.ctrl_type = ctrl_type
        self.num_rows = num_rows
        self.timekeys_start = timekeys_start
        self.values_start = values_start
        self.num_columns = num_columns


class ControllerRow:
    def __init__(self, timekey, values):
        self.timekey = timekey
        self.values = values

    def __repr__(self):
        return "{{timekey={}, values={}}}".format(self.timekey, self.values)


class ArrayDefinition:
    def __init__(self, offset, count):
        self.offset = offset
        self.count = count


class MdlLoader:

    def __init__(self, path):
        self.mdl = BinaryReader(path, 'little')

        base, _ = os.path.splitext(path)
        mdx_path = base + ".mdx"
        if not os.path.exists(mdx_path):
            raise MdxNotFound("MDX file '{}' not found".format(mdx_path))

        self.mdx = BinaryReader(mdx_path, 'little')

    def load(self):
        self.load_file_header()
        self.load_geometry_header()
        self.load_model_header()
        self.load_names()

        root_node = self.load_nodes(self.off_root_node)

        return Model(
            self.model_name,
            self.supermodel_name,
            root_node
            )

    def load_file_header(self):
        if self.mdl.get_uint32() != 0:
            raise MalformedMdl("Invalid MDL signature")
        self.mdl_size = self.mdl.get_uint32()
        self.mdx_size = self.mdl.get_uint32()

    def load_geometry_header(self):
        fn_ptr1 = self.mdl.get_uint32()
        self.tsl = fn_ptr1 in [FN_PTR_1_K2_PC, FN_PTR_1_K2_XBOX]
        self.xbox = fn_ptr1 in [FN_PTR_1_K1_XBOX, FN_PTR_1_K2_XBOX]
        fn_ptr2 = self.mdl.get_uint32()
        self.model_name = self.mdl.get_c_string_up_to(32)
        self.off_root_node = self.mdl.get_uint32()
        total_num_nodes = self.mdl.get_uint32()
        runtime_arr1 = self.get_array_def()
        runtime_arr2 = self.get_array_def()
        ref_count = self.mdl.get_uint32()
        self.model_type = self.mdl.get_uint8()
        if self.model_type != 2:
            raise MalformedMdl("Invalid model type: expected=2, actual={}".format(self.model_type))
        self.mdl.skip(3) # padding

    def load_model_header(self):
        classification = self.mdl.get_uint8()
        subclassification = self.mdl.get_uint8()
        self.mdl.skip(1) # unknown
        affected_by_fog = self.mdl.get_uint8()
        num_child_models = self.mdl.get_uint32()
        animation_arr = self.get_array_def()
        supermodel_ref = self.mdl.get_uint32()
        bounding_box = [self.mdl.get_float() for _ in range(6)]
        radius = self.mdl.get_float()
        scale = self.mdl.get_float()
        self.supermodel_name = self.mdl.get_c_string_up_to(32)
        off_head_root_node = self.mdl.get_uint32()
        self.mdl.skip(4) # padding
        mdx_size = self.mdl.get_uint32()
        if mdx_size != self.mdx_size:
            raise MalformedMdl("MDX size mismatch: expected={}, actual={}".format(self.mdx_size, mdx_size))
        mdx_offset = self.mdl.get_uint32()
        self.name_arr = self.get_array_def()

    def load_names(self):
        self.names = []
        self.mdl.seek(MDL_OFFSET + self.name_arr.offset)
        offsets = [self.mdl.get_uint32() for _ in range(self.name_arr.count)]
        for off in offsets:
            self.mdl.seek(MDL_OFFSET + off)
            self.names.append(self.mdl.get_c_string())

    def load_nodes(self, offset, parent=None):
        self.mdl.seek(MDL_OFFSET + offset)

        node_type = self.mdl.get_uint16()
        supernode_number = self.mdl.get_uint16()
        name_index = self.mdl.get_uint16()
        self.mdl.skip(2) # padding
        off_root = self.mdl.get_uint32()
        off_parent = self.mdl.get_uint32()
        position = [self.mdl.get_float() for _ in range(3)]
        orientation = [self.mdl.get_float() for _ in range(4)]
        children_arr = self.get_array_def()
        controller_arr = self.get_array_def()
        controller_data_arr = self.get_array_def()

        node = ModelNode(
            self.names[name_index],
            self.get_node_type(node_type),
            parent,
            position,
            orientation
            )

        if node_type & NODE_LIGHT:
            flare_radius = self.mdl.get_float()
            unknown_arr = self.get_array_def()
            flare_size_arr = self.get_array_def()
            flare_position_arr = self.get_array_def()
            flare_color_shift_arr = self.get_array_def()
            flare_texture_name_arr = self.get_array_def()
            light_priority = self.mdl.get_uint32()
            ambient_only = self.mdl.get_uint32()
            dynamic_type = self.mdl.get_uint32()
            affect_dynamic = self.mdl.get_uint32()
            shadow = self.mdl.get_uint32()
            flare = self.mdl.get_uint32()
            fading_light = self.mdl.get_uint32()

        if node_type & NODE_EMITTER:
            pass
        if node_type & NODE_REFERENCE:
            pass

        if node_type & NODE_MESH:
            fn_ptr1 = self.mdl.get_uint32()
            fn_ptr2 = self.mdl.get_uint32()
            face_arr = self.get_array_def()
            bouding_box = [self.mdl.get_float() for _ in range(6)]
            radius = self.mdl.get_float()
            average = [self.mdl.get_float() for _ in range(3)]
            diffuse = [self.mdl.get_float() for _ in range(3)]
            ambient = [self.mdl.get_float() for _ in range(3)]
            transparency_hint = self.mdl.get_uint32()
            bitmap1 = self.mdl.get_c_string_up_to(32)
            bitmap2 = self.mdl.get_c_string_up_to(32)
            bitmap3 = self.mdl.get_c_string_up_to(12)
            bitmap4 = self.mdl.get_c_string_up_to(12)
            index_count_arr = self.get_array_def()
            index_offset_arr = self.get_array_def()
            inv_counter_arr = self.get_array_def()
            self.mdl.skip(3 * 4) # unknown
            self.mdl.skip(8) # saber unknown
            animate_uv = self.mdl.get_uint32()
            uv_dir_x = self.mdl.get_float()
            uv_dir_y = self.mdl.get_float()
            uv_jitter = self.mdl.get_float()
            uv_jitter_speed = self.mdl.get_float()
            mdx_data_size = self.mdl.get_uint32()
            mdx_data_bitmap = self.mdl.get_uint32()
            off_mdx_verts = self.mdl.get_uint32()
            off_mdx_normals = self.mdl.get_uint32()
            off_mdx_colors = self.mdl.get_uint32()
            off_mdx_uv1 = self.mdl.get_uint32()
            off_mdx_uv2 = self.mdl.get_uint32()
            off_mdx_uv3 = self.mdl.get_uint32()
            off_mdx_uv4 = self.mdl.get_uint32()
            off_mdx_tan_space1 = self.mdl.get_uint32()
            off_mdx_tan_space2 = self.mdl.get_uint32()
            off_mdx_tan_space3 = self.mdl.get_uint32()
            off_mdx_tan_space4 = self.mdl.get_uint32()
            num_verts = self.mdl.get_uint16()
            num_textures = self.mdl.get_uint16()
            has_lightmap = self.mdl.get_uint8()
            rotate_texture = self.mdl.get_uint8()
            background_geometry = self.mdl.get_uint8()
            shadow = self.mdl.get_uint8()
            beaming = self.mdl.get_uint8()
            render = self.mdl.get_uint8()

            if self.tsl:
                dirt_enabled = self.mdl.get_uint8()
                self.mdl.skip(1) # padding
                dirt_texture = self.mdl.get_uint16()
                dirt_coord_space = self.mdl.get_uint16()
                hide_in_holograms = self.mdl.get_uint8()
                self.mdl.skip(1) # padding

            self.mdl.skip(2) # padding
            total_area = self.mdl.get_float()
            self.mdl.skip(4) # padding
            mdx_offset = self.mdl.get_uint32()

            if not self.xbox:
                off_vert_arr = self.mdl.get_uint32()

        if node_type & NODE_SKIN:
            pass
        if node_type & NODE_DANGLY:
            pass
        if node_type & NODE_AABB:
            pass
        if node_type & NODE_SABER:
            pass

        if controller_arr.count > 0:
            self.mdl.seek(MDL_OFFSET + controller_arr.offset)
            keys = []
            for _ in range(controller_arr.count):
                ctrl_type = self.mdl.get_uint32()
                self.mdl.skip(2) # unknown
                num_rows = self.mdl.get_uint16()
                timekeys_start = self.mdl.get_uint16()
                values_start = self.mdl.get_uint16()
                num_columns = self.mdl.get_uint8()
                self.mdl.skip(3) # padding
                keys.append(ControllerKey(ctrl_type, num_rows, timekeys_start, values_start, num_columns))
            controllers = dict()
            for key in keys:
                self.mdl.seek(MDL_OFFSET + controller_data_arr.offset + 4 * key.timekeys_start)
                timekeys = [self.mdl.get_float() for _ in range(key.num_rows)]
                self.mdl.seek(MDL_OFFSET + controller_data_arr.offset + 4 * key.values_start)
                if key.ctrl_type == CTRL_BASE_ORIENTATION and key.num_columns == 2:
                    num_columns = 1
                else:
                    num_columns = key.num_columns & 0xf
                    bezier = key.num_columns & 0x10
                    if bezier:
                        num_columns *= 3
                values = [self.mdl.get_float() for _ in range(num_columns * key.num_rows)]
                controllers[key.ctrl_type] = [ControllerRow(timekeys[i], values[i*key.num_columns:i*key.num_columns+num_columns]) for i in range(key.num_rows)]
            if node_type & NODE_LIGHT:
                node.color = controllers[CTRL_LIGHT_COLOR][0].values if CTRL_LIGHT_COLOR in controllers else 3 * [1.0]
                node.radius = controllers[CTRL_LIGHT_RADIUS][0].values[0] if CTRL_LIGHT_RADIUS in controllers else 1.0
                node.multiplier = controllers[CTRL_LIGHT_MULTIPLIER][0].values[0] if CTRL_LIGHT_MULTIPLIER in controllers else 1.0

        if node_type & NODE_MESH:
            node.facelist = FaceList()
            if face_arr.count > 0:
                self.mdl.seek(MDL_OFFSET + face_arr.offset)
                for _ in range(face_arr.count):
                    normal = [self.mdl.get_float() for _ in range(3)]
                    plane_distance = self.mdl.get_float()
                    material_id = self.mdl.get_uint32()
                    adjacent_faces = [self.mdl.get_uint16() for _ in range(3)]
                    vert_indices = [self.mdl.get_uint16() for _ in range(3)]
                    node.facelist.faces.append(tuple(vert_indices))
                if index_count_arr.count > 0:
                    self.mdl.seek(MDL_OFFSET + index_count_arr.offset)
                    num_indices = self.mdl.get_uint32()
                if index_offset_arr.count > 0:
                    self.mdl.seek(MDL_OFFSET + index_offset_arr.offset)
                    off_indices = self.mdl.get_uint32()

            node.verts = []
            for i in range(num_verts):
                self.mdx.seek(mdx_offset + i * mdx_data_size + off_mdx_verts)
                node.verts.append(tuple([self.mdx.get_float() for _ in range(3)]))

        self.mdl.seek(MDL_OFFSET + children_arr.offset)
        child_offsets = [self.mdl.get_uint32() for _ in range(children_arr.count)]
        for off_child in child_offsets:
            child = self.load_nodes(off_child, node)
            node.children.append(child)

        return node

    def get_node_type(self, flags):
        if flags & NODE_SABER:
            return Nodetype.LIGHTSABER
        if flags & NODE_AABB:
            return Nodetype.AABB
        if flags & NODE_DANGLY:
            return Nodetype.DANGLYMESH
        if flags & NODE_SKIN:
            return Nodetype.SKIN
        if flags & NODE_MESH:
            return Nodetype.TRIMESH
        if flags & NODE_REFERENCE:
            return Nodetype.REFERENCE
        if flags & NODE_EMITTER:
            return Nodetype.EMITTER
        if flags & NODE_LIGHT:
            return Nodetype.LIGHT
        return Nodetype.DUMMY

    def get_array_def(self):
        offset = self.mdl.get_uint32()
        count1 = self.mdl.get_uint32()
        count2 = self.mdl.get_uint32()
        if count1 != count2:
            raise MalformedMdl("Array count mismatch: count1={}, count2={}".format(count1, count2))

        return ArrayDefinition(offset, count1)