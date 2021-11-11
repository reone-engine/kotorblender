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

import bpy

from ... import defines


class KB_PT_mesh(bpy.types.Panel):
    bl_label = "Odyssey Mesh"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return (context.object and
                context.object.type == 'MESH' and
                context.object.kb.meshtype != defines.Meshtype.EMITTER)

    def draw(self, context):
        obj = context.object
        layout = self.layout

        row = layout.row()
        row.prop(obj.kb, "meshtype", text="Type")
        row = layout.row()
        row.prop(obj.kb, "node_number")
        row = layout.row()
        row.prop(obj.kb, "export_order")

        layout.separator()

        row = layout.row()
        box = row.box()
        row = box.row()
        row.prop_search(obj.kb, "bitmap", bpy.data, "images")
        row = box.row()
        row.prop_search(obj.kb, "bitmap2", bpy.data, "images")
        row = box.row()
        row.prop(obj.kb, "diffuse")
        row = box.row()
        row.prop(obj.kb, "ambient")
        row = box.row()
        row.prop(obj.kb, "selfillumcolor")
        row = box.row()
        row.prop(obj.kb, "alpha")
        row = box.row()
        row.operator("kb.rebuild_materials")

        row = layout.row()
        box = row.box()
        split = box.split()
        col = split.column()
        col.prop(obj.kb, "render", text="Render")
        col.prop(obj.kb, "shadow", text="Shadow")
        col.prop(obj.kb, "lightmapped", text="Lightmapped")
        col.prop(obj.kb, "tangentspace", text="Tangentspace")
        col.prop(obj.kb, "background_geometry", text="Background Geometry")
        col = split.column()
        col.prop(obj.kb, "beaming", text="Beaming")
        col.prop(obj.kb, "inheritcolor", text="Inherit Color")
        col.prop(obj.kb, "rotatetexture", text="Rotate Texture")
        col.prop(obj.kb, "hologram_donotdraw")
        row = box.row()
        row.prop(obj.kb, "transparencyhint", text="Transparency Hint")
        row = box.row()
        row.prop(obj.kb, "animateuv")
        if obj.kb.animateuv:
            row = box.row()
            split = box.split()
            col = split.column()
            col.prop(obj.kb, "uvdirectionx")
            col.prop(obj.kb, "uvjitter")
            col = split.column()
            col.prop(obj.kb, "uvdirectiony")
            col.prop(obj.kb, "uvjitterspeed")
        row = box.row()
        row.prop(obj.kb, "dirt_enabled")
        if obj.kb.dirt_enabled:
            row = box.row()
            row.prop(obj.kb, "dirt_texture")
            row = box.row()
            row.prop(obj.kb, "dirt_worldspace")

        # Additional props for danglymeshes
        if obj.kb.meshtype == defines.Meshtype.DANGLYMESH:
            layout.separator()

            row = layout.row()
            box = row.box()
            row = box.row()
            row.label(text="Danglymesh Properties")
            row = box.row()
            row.prop_search(obj.kb, "constraints", obj, "vertex_groups", text="Constraints")
            row = box.row()
            row.prop(obj.kb, "period", text="Period")
            row = box.row()
            row.prop(obj.kb, "tightness", text="Tightness")
            row = box.row()
            row.prop(obj.kb, "displacement", text="Displacement")

        # Additional props for aabb walkmeshes
        elif obj.kb.meshtype == defines.Meshtype.AABB:
            layout.separator()

            row = layout.row()
            box = row.box()
            row = box.row()
            row.prop(obj.kb, "bwmposition", text="BWM Position")
            row = box.row()
            row.prop(obj.kb, "lytposition", text="LYT Position")
            row = box.row()
            row.operator("kb.load_wok_mats", text="Load walkmesh materials", icon='NONE')
