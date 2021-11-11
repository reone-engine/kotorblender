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

from bpy_extras import image_utils

from . import glob


def create_image(name, path):
    image = image_utils.load_image(
        name + ".tga",
        path,
        recursive=glob.texture_search_recursive,
        place_holder=False,
        ncase_cmp=True)

    if image is None:
        image = bpy.data.images.new(name, 512, 512)
    else:
        image.name = name

    return image


def load_texture_image(name):
    if name in bpy.data.textures:
        texture = bpy.data.textures[name]
    else:
        if name in bpy.data.images:
            image = bpy.data.images[name]
        else:
            image = create_image(name, glob.texture_path)

        texture = bpy.data.textures.new(name, type='IMAGE')
        texture.image = image
        texture.use_fake_user = True

    return texture.image
