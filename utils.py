import pyglet
import ratcave as rc
from collections import namedtuple
# from pypixxlib import propixx
import json
import logging
import cfg

RenderCollection = namedtuple("RenderCollection", "shader fbo quad")


# def setup_window(screen=1, fullscreen=True):
    # """Return a pyglet Window on the screen desired."""
    # display = pyglet.window.get_platform().get_default_display()
    # screen = display.get_screens()[screen]
    # window = pyglet.window.Window(fullscreen=fullscreen, screen=screen, vsync=False)
    # return window


# def setup_cube_fbo(width=4096):
    # """Return a ratcave FBO instance, pre-loaded with a TextureCube of length 'width'."""
    # return rc.FBO(texture=rc.TextureCube(width=4096, height=4096))


# def get_arena_with_rigidbody(arena_objfilename, motive_client, flat_shading=False, objname='Arena'):
    # """Return (arena, arena_rb) from filename and motive client."""
    # arena = rc.WavefrontReader(arena_objfilename).get_mesh(objname)
    # arena.uniforms['diffuse'] = 1., 1, 1
    # arena.rotation = arena.rotation.to_quaternion()

    # arena_rb = motive_client.rigid_bodies['Arena']
    # arena.position.xyz = arena_rb.position
    # arena.rotation.wxyz = arena_rb.quaternion
    # arena.uniforms['flat_shading'] = flat_shading

    # return arena, arena_rb


# def get_beamer_camera(fname, aspect=1.7778, fov_y=41.5):
    # """Load ratcave CAmera from pickle file and apply aspect ratio and fov_y intrinsics."""
    # beamer = rc.Camera.from_pickle(fname)
    # beamer.projection.aspect = aspect
    # beamer.projection.fov_y = fov_y
    # return beamer


# Load up Meshes and Scene
def load_projected_scene(arena_file, projector_file, motive_client):
    """Scene-building convenience function. Returns (scene, arena, arena_rb) from filenames and motive."""
    arena, arena_rb = get_arena_with_rigidbody(arena_objfilename=arena_file, motive_client=motive_client)
    beamer = get_beamer_camera(fname=projector_file)
    scene = rc.Scene(meshes=[arena], bgColor=(.6, 0, 0))
    scene.camera.position.xyz = beamer.position.xyz
    scene.camera.rotation.xyz = beamer.rotation.xyz
    scene.camera.projection.fov_y = beamer.projection.fov_y
    scene.camera.projection.aspect = beamer.projection.aspect
    scene.gl_states = scene.gl_states[:-1]
    scene.light.position.xyz = beamer.position.xyz
    return scene, arena, arena_rb


def get_cubecamera(z_near=.004, z_far=1.5):
    """Returns a ratcave.Camera instance with fov_y=90 and aspect=1. Useful for dynamic cubemapping."""
    camera = rc.Camera(projection=rc.PerspectiveProjection(fov_y=90., aspect=1., z_near=z_near, z_far=z_far))
    camera.rotation = camera.rotation.to_quaternion()
    return camera


def load_virtual_scene(active_scene, bgColor=(0., 0., 0.)):
    """Return a scene with a cube camera and a light in the same position as the active_scene's light."""
    scene = rc.Scene(meshes=[], bgColor=bgColor, camera=get_cubecamera())
    scene.light.position.xyz = active_scene.light.position.xyz
    scene.gl_states = scene.gl_states[:-1]
    return scene


def get_virtual_arena_mesh(arena_file, arena_mesh, objname='Arena', texture_filename=None):
    """Returns an arena mesh parented to another arena meesh and with lighting settings applied."""
    vr_arena = rc.WavefrontReader(arena_file).get_mesh(objname)
    vr_arena.uniforms['diffuse'] = 1., 1, 1
    vr_arena.parent = arena_mesh
    vr_arena.uniforms['flat_shading'] = False
    if texture_filename:
        vr_arena.texture = rc.Texture.from_image(texture_filename)
    return vr_arena





def update(dt, arena, cube_camera, motive_client):
    arena.position.xyz = motive_client.rigid_bodies['Arena'].position
    arena.rotation.xyzw = motive_client.rigid_bodies['Arena'].quaternion

    cube_camera.position.xyz = motive_client.rigid_bodies['Rat'].position
    cube_camera.rotation.xyzw = motive_client.rigid_bodies['Rat'].quaternion
    cube_camera.uniforms['playerPos'] = cube_camera.position.xyz

def setup_deferred_rendering():
    """Return (Shader, FBO, QuadMesh) for deferred rendering."""
    fbo = rc.FBO(rc.Texture(width=4096, height=4096, mipmap=True))
    quad = rc.gen_fullscreen_quad("DeferredQuad")
    quad.texture = fbo.texture
    shader = rc.Shader.from_file(*rc.resources.deferredShader)
    return RenderCollection(shader=shader, fbo=fbo, quad=quad)


def setup_grey3x_rendering(update_projector=False):
    """
    Return (Shader, FBO, QuadMesh) for rendering in Propixx's 'GREY3X' mode. If desired, can
    also apply the settings to the beamer to set it to this mode (caution: won't change back afterward).
    """

    if update_projector:
        beamer = propixx.PROPixx()
        beamer.setDlpSequencerProgram('GREY3X')

    vert_shader = open(rc.resources.deferredShader.vert).read()
    frag_shader = """
    #version 400
    #extension GL_ARB_texture_rectangle : enable

    uniform sampler2D TextureMap;

    in vec2 texCoord;
    out vec3 color;

    void main( void ) {

        if (gl_FragCoord.x * 3 + 1 < 1920){
            color = vec3(texture2D(TextureMap, vec2(floor(gl_FragCoord.x * 3. + 0.0) / 1920.0, gl_FragCoord.y / 1080.0)).r,
                         texture2D(TextureMap, vec2(floor(gl_FragCoord.x * 3. + 1.0) / 1920.0, gl_FragCoord.y / 1080.0)).r,
                         texture2D(TextureMap, vec2(floor(gl_FragCoord.x * 3. + 2.0) / 1920.0, gl_FragCoord.y / 1080.0)).r
                         );

        } else {
            color = vec3(.2, 0., 0.);
        }
        return;
    }
    """

    shader = rc.Shader(vert=vert_shader, frag=frag_shader)
    quad = rc.gen_fullscreen_quad('Grey3xQuad')
    return RenderCollection(shader=shader, fbo=None, quad=quad)


def create_and_configure_experiment_logs(filename, motive_client, exclude_subnames=[]):
    """
    Sets the csv logging config and writes the json sesssion config log from cfg.py, excluding all variables that contain
    any of the substrings in 'exclude_subnames'.
    """
    filename_settings = 'logs/settings_logs/' + filename + '.json'
    with open(filename_settings, 'w') as f:
        json.dump({var: cfg.__dict__[var] for var in dir(cfg) if not '_' in var[0] and not any(substring in var for substring in exclude_subnames)}, f, sort_keys=True, indent=4)

    filename_log = 'logs/events_logs/' + filename + '.csv'
    with open(filename_log, 'a') as f:
        f.write('DateTime; MotiveExpTimeSecs; Event; EventArguments\n')

    logging.basicConfig(filename=filename_log,
                        level=logging.INFO, format='%(asctime)s; %(message)s')

    motive_client.set_take_file_name(file_name=filename)
