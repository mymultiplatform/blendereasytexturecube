# Blender Python: Isometric cube + box-mapped texture + extreme bump (version-safe)
# - No hard-coded input names that break on 4.x
# - Uses BOX projection to avoid stretching
# - Uses image colorspace (Non-Color) for height on Bump
# - Orthographic isometric camera
# - Optional render to Desktop

import bpy, os, math

# -------- CONFIG --------
tex_path = r"C:\Users\PCEL SERVICE\Desktop\groovy_scales_5.png"
out_path = os.path.join(os.path.expanduser("~"), "Desktop", "cube_isometric.png")
render_now = True  # set False to skip rendering

# -------- CLEAN SCENE --------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# -------- CUBE --------
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
cube = bpy.context.active_object
bpy.ops.object.shade_flat()

# -------- CAMERA (ORTHOGRAPHIC + ISOMETRIC) --------
bpy.ops.object.camera_add()
cam = bpy.context.active_object
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 5.0
cam.location = (10, -10, 10)
cam.rotation_euler = (math.radians(60), 0.0, math.radians(45))
bpy.context.scene.camera = cam

# -------- WORLD (EVEN ENV LIGHT) --------
world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes
wl = world.node_tree.links
for n in list(wn):
    if n.type != "OUTPUT_WORLD":
        wn.remove(n)
bg = wn.new("ShaderNodeBackground")
bg.inputs[0].default_value = (1, 1, 1, 1)
bg.inputs[1].default_value = 1.2
wout = [n for n in wn if n.type == "OUTPUT_WORLD"][0]
wl.new(bg.outputs["Background"], wout.inputs["Surface"])

# -------- MATERIAL (BOX PROJECTION + EXTREME BUMP) --------
mat = bpy.data.materials.new("RainbowFish_Box_Bump")
mat.use_nodes = True
nt = mat.node_tree
nodes = nt.nodes
links = nt.links

# Clear nodes except output
for n in list(nodes):
    if n.type != 'OUTPUT_MATERIAL':
        nodes.remove(n)
out = [n for n in nodes if n.type == 'OUTPUT_MATERIAL'][0]

# Principled BSDF
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
bsdf.location = (-80, 0)
# Leave specular/ior defaults to avoid API name changes across versions
# Set moderate roughness via safe check
rough = bsdf.inputs.get("Roughness")
if rough: rough.default_value = 0.25

# Coordinate + Mapping
texcoord = nodes.new("ShaderNodeTexCoord")
texcoord.location = (-1100, 100)
mapping = nodes.new("ShaderNodeMapping")
mapping.location = (-900, 100)
mapping.inputs["Scale"].default_value = (0.5, 0.5, 0.5)  # denser pattern

# Load image once
if not os.path.isfile(tex_path):
    raise FileNotFoundError(f"Texture not found: {tex_path}")
img = bpy.data.images.load(tex_path, check_existing=True)

# COLOR texture node (sRGB)
tex_color = nodes.new("ShaderNodeTexImage")
tex_color.location = (-650, 140)
tex_color.image = img
tex_color.interpolation = 'Cubic'
tex_color.projection = 'BOX'
tex_color.projection_blend = 0.25  # soften seams
# HEIGHT texture node (Non-Color)
tex_height = nodes.new("ShaderNodeTexImage")
tex_height.location = (-650, -180)
tex_height.image = img
tex_height.interpolation = 'Cubic'
tex_height.projection = 'BOX'
tex_height.projection_blend = 0.25
# IMPORTANT: colorspace is on the IMAGE, not the node:
img.colorspace_settings.name = 'sRGB'        # keep color map sRGB
# For height sampling, we need non-color; duplicate image datablock safely:
img_nc = img.copy()
img_nc.colorspace_settings.name = 'Non-Color'
tex_height.image = img_nc

# Convert color->height
rgb2bw = nodes.new("ShaderNodeRGBToBW")
rgb2bw.location = (-430, -180)

# Extreme bump
bump = nodes.new("ShaderNodeBump")
bump.location = (-220, -180)
bump.inputs["Strength"].default_value = 2.0   # strong depth
bump.inputs["Distance"].default_value = 1.0   # height scale

# Links
links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
links.new(mapping.outputs["Vector"], tex_color.inputs["Vector"])
links.new(mapping.outputs["Vector"], tex_height.inputs["Vector"])

links.new(tex_color.outputs["Color"], bsdf.inputs["Base Color"])
links.new(tex_height.outputs["Color"], rgb2bw.inputs["Color"])
links.new(rgb2bw.outputs["Val"], bump.inputs["Height"])
links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

# Assign material to cube
if cube.data.materials:
    cube.data.materials[0] = mat
else:
    cube.data.materials.append(mat)

# -------- RENDER SETTINGS --------
scene = bpy.context.scene
scene.render.engine = 'CYCLES'     # better bump response
scene.cycles.feature_set = 'SUPPORTED'
scene.cycles.samples = 128
scene.render.resolution_x = 1200
scene.render.resolution_y = 1200
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.film_transparent = True
scene.render.filepath = out_path

# -------- OPTIONAL RENDER --------
if render_now:
    bpy.ops.render.render(write_still=True)
    print(f"Saved isometric cube render: {out_path}")
