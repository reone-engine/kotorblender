"""
Material management, including composing and traversing of shader node trees.
"""

import bpy

from . import nvb_glob, nvb_teximage, nvb_utils


def _get_material_name(node):
    """
    Get material name of the model node.
    """
    # Diffuse texture or diffuse color
    if not nvb_utils.isNull(node.bitmap):
        result = "D" + node.bitmap
    else:
        result = "D" + nvb_utils.colorToHex(node.diffuse)

    # Alpha
    result += "__A" + nvb_utils.intToHex(nvb_utils.floatToByte(node.alpha))

    return result


def load_material(node, name):
    """
    Get or create a material.
    """
    # If material reuse is enabled, search for existing material
    if nvb_glob.materialMode == 'SIN' and node.lightmapped == 0:
        material_name = _get_material_name(node)
        if material_name in bpy.data.materials:
            material = bpy.data.materials[material_name]
            if material:
                return material
    else:
        material_name = name

    material = bpy.data.materials.new(material_name)

    # Diffuse texture
    if not nvb_utils.isNull(node.bitmap):
        material.use_nodes = True
        links = material.node_tree.links
        links.clear()
        nodes = material.node_tree.nodes
        nodes.clear()

        diffuse = nodes.new('ShaderNodeTexImage')
        diffuse.location = (300, 0)
        diffuse.image = nvb_teximage.load_texture_image(node.bitmap, node.tangentspace == 1)

        mul_alpha = nodes.new('ShaderNodeMath')
        mul_alpha.location = (600, -300)
        mul_alpha.operation = 'MULTIPLY'
        mul_alpha.inputs[1].default_value = node.alpha

        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.location = (900, 0)

        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (1200, 0)

        # Lightmap texture
        if not nvb_utils.isNull(node.bitmap2):
            material.shadow_method = 'NONE'

            lightmap_uv = nodes.new('ShaderNodeUVMap')
            lightmap_uv.location = (0, -300)
            lightmap_uv.uv_map = name+'_lm.uv'

            lightmap = nodes.new('ShaderNodeTexImage')
            lightmap.location = (300, -300)
            lightmap.image = nvb_teximage.load_image(node.bitmap2)

            mul_diffuse_by_lightmap = nodes.new('ShaderNodeVectorMath')
            mul_diffuse_by_lightmap.location = (600, 0)
            mul_diffuse_by_lightmap.operation = 'MULTIPLY'

            links.new(lightmap.inputs[0], lightmap_uv.outputs[0])
            links.new(mul_diffuse_by_lightmap.inputs[0], diffuse.outputs[0])
            links.new(mul_diffuse_by_lightmap.inputs[1], lightmap.outputs[0])
            links.new(bsdf.inputs['Base Color'], mul_diffuse_by_lightmap.outputs[0])
        else:
            links.new(bsdf.inputs['Base Color'], diffuse.outputs[0])

        links.new(mul_alpha.inputs[0], diffuse.outputs[1])
        links.new(bsdf.inputs['Alpha'], mul_alpha.outputs[0])
        links.new(bsdf.outputs[0], output.inputs[0])
    else:
        material.diffuse_color = [*node.diffuse, 1.0]

    return material


def get_output_material_node(material):
    """
    Searches for Material Output node in the materials node tree.
    """
    if material.use_nodes:
        return next(node for node in material.node_tree.nodes if node.bl_idname == 'ShaderNodeOutputMaterial')
    else:
        return None


def get_bsdf_principled_node(parent):
    """
    Searches for Principled BSDF node starting from the Material Output.
    """
    if parent and parent.inputs[0].is_linked:
        node = parent.inputs[0].links[0].from_node
        if node.bl_idname == 'ShaderNodeBsdfPrincipled':
            return node

    return None


def get_diffuse_image(parent):
    """
    Searches for a diffuse texture image starting from the shader node.
    """
    if parent:
        color_input = parent.inputs['Base Color']
        if color_input.is_linked:
            # Assume that VectorMath input means Diffuse+Lightmap setup, Diffuse only otherwise
            node = color_input.links[0].from_node
            if node.bl_idname == 'ShaderNodeVectorMath':
                if node.inputs[0].is_linked:
                    node = node.inputs[0].links[0].from_node
                    if node.bl_idname == 'ShaderNodeTexImage':
                        return node.image
            elif node.bl_idname == 'ShaderNodeTexImage':
                return node.image

    return None


def get_aurora_alpha(parent):
    """
    Searches for Aurora alpha value starting from the shader node.
    """
    if parent:
        alpha_input = parent.inputs['Alpha']
        if alpha_input.is_linked:
            node = alpha_input.links[0].from_node
            if node.bl_idname == 'ShaderNodeMath':
                return node.inputs[1].default_value

    return 1.0


def get_lightmap_image(parent):
    """
    Searches for a lightmap texture image starting from the shader node.
    """
    if parent:
        color_input = parent.inputs['Base Color']
        if color_input.is_linked:
            node = color_input.links[0].from_node
            if node.bl_idname == 'ShaderNodeVectorMath' and node.inputs[1].is_linked:
                node = node.inputs[1].links[0].from_node
                if node.bl_idname == 'ShaderNodeTexImage':
                    return node.image

    return None
