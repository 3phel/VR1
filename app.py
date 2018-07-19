from __future__ import print_function

#
# {'stereo': 0,
#  'buffer_size': 32,
#  'aux_buffers': 4,
#  'sample_buffers': 0,
#  'samples': 0,
#  'red_size': 8,
#  'green_size': 8,
#  'blue_size': 8,
#  'alpha_size': 0,
#  'depth_size': 24,
#  'stencil_size': 0,
#  'accum_red_size': 16,
#  'accum_blue_size': 16,
#  'accum_green_size': 16,
#  'accum_alpha_size': 16,
#  'major_version': None,
#  'minor_version': None,
#  'forward_compatible': None,
#  'debug': None,
#  }

import pyglet
import pyglet.gl as gl
import numpy as np
pyglet.options['debug_gl'] = False
pyglet.options['debug_gl_trace'] = False

import ratcave as rc
from natnetclient import NatClient
import utils
import cfg

motive = NatClient(read_rate=2000, )
if not motive.rigid_bodies:
    raise IOError("Not Detecting Rigid Bodies.  Turn RigidBody Streaming On in the Motive Streaming Pane.")

if not motive.rigid_bodies[cfg.ARENA_MESH_NAME].position:
    raise IOError("Not Detecting Arena Position.  Turn RigidBody Streaming on in the Motive Streaming Pane.")


class RatcaveApp(pyglet.window.Window):
    def __init__(self, arena_objfile, projector_file, fullscreen=True, screen=1, antialiasing=True, vsync=False,
                 fps_mode=False, *args, **kwargs):
        """
        A Pyglet Window that sets up the arena, beamer, and virtual scenes, along with motive update and draw functions
        for updating and rendering a virtual reality environment in a ratCAVE setup.
        """
        self.__display = pyglet.window.get_platform().get_default_display()
        self.__screen = self.__display.get_screens()[screen]
        super(self.__class__, self).__init__(fullscreen=fullscreen, screen=self.__screen, vsync=vsync, *args, **kwargs)

        self.cube_fbo = rc.FBO(texture=rc.TextureCube(width=4096, height=4096))

        
        self.arena = rc.WavefrontReader(arena_objfile).get_mesh(cfg.ARENA_MESH_NAME)
        self.arena.uniforms['diffuse'] = cfg.ARENA_LIGHTING_DIFFUSE
        self.arena.uniforms['flat_shading'] = cfg.ARENA_LIGHTING_FLAT_SHADING
        self.arena.rotation = self.arena.rotation.to_quaternion()

        self.arena_rb = motive.rigid_bodies[cfg.ARENA_MOTIVE_NAME]
        self.arena.position.xyz = self.arena_rb.position
        self.arena.rotation.wxyz = self.arena_rb.quaternion
        
        beamer = rc.Camera.from_pickle(projector_file)      
        beamer.projection.aspect = 1.77778
        beamer.projection.fov_y = 41.5
        
        self.active_scene = rc.Scene(meshes=[self.arena], bgColor=(.6, 0, 0), camera=beamer)
        self.active_scene.gl_states.states = self.active_scene.gl_states.states[:-1]
        self.active_scene.light.position.xyz = beamer.position.xyz

        self.orig_texture = None

        self.shader = rc.resources.cube_shader
        self._vr_scenes = set()
        self.current_vr_scene = None

        self.rodent_rb = motive.rigid_bodies[cfg.RODENT_MOTIVE_NAME]

        # self.antialiasing = antialiasing
        # self.fbo_aa = rc.FBO(rc.Texture(width=4096, height=4096, mipmap=True))
        # self.aa_quad = rc.gen_fullscreen_quad()
        # self.aa_quad.texture = self.fbo_aa.texture
        # self.shader_deferred = rc.Shader.from_file(*rc.resources.deferredShader)
        # if fps_mode:
            # pass
            # # raise NotImplementedError("Haven't gotten fps_mode to work properly yet.")
        # self.fps_mode = fps_mode

        pyglet.clock.schedule(self.update)

    # def on_draw(self):
    #     """Render the virtual environment."""
    #     if self.fps_mode:
    #         with self.shader:
    #             if self.current_vr_scene:
    #                 self.current_vr_scene.draw()
    #             else:
    #                 self.active_scene.draw()
    #     else:
    #         with self.shader:
    #             if self.current_vr_scene:
    #                 with self.cube_fbo as fbo:
    #
    #                     self.current_vr_scene.draw360_to_texture_anaglyphed(fbo.texture)
    #             if self.antialiasing:
    #                 with self.fbo_aa:
    #                     self.active_scene.draw()
    #             else:
    #                 self.active_scene.draw()
    #
    #         if self.antialiasing:
    #             with self.shader_deferred:
    #                 self.aa_quad.draw()


    # def on_draw(self):
    #     """new anaglyph drawing function."""
    #     if self.current_vr_scene:
    #         # One eye
    #         with self.shader:
    #             gl.glColorMask(True, False, False, True)
    #             cam = self.current_vr_scene.camera
    #             orig_cam_position = cam.position.xyz
    #             # import ipdb
    #             # ipdb.set_trace()
    #             cam.position.xyz = cam.model_matrix.dot([.02 / 2., 0., 0., 1.])[:3]  # inter_eye_distance / 2.
    #
    #             cam.uniforms['playerPos'] = cam.position.xyz
    #             if self.current_vr_scene:
    #                 with self.cube_fbo as fbo:
    #                     self.current_vr_scene.draw360_to_texture(fbo.texture)
    #             self.active_scene.draw()
    #
    #             cam.position.xyz = orig_cam_position
    #
    #         # Other eye
    #         with self.shader:
    #             gl.glColorMask(False, True, True, True)
    #             cam.position.xyz = cam.model_matrix.dot([-.02 / 2., 0., 0., 1.])[:3]
    #             cam.uniforms['playerPos'] = cam.position.xyz
    #             if self.current_vr_scene:
    #                 with self.cube_fbo as fbo:
    #                     self.current_vr_scene.draw360_to_texture(fbo.texture)
    #             self.active_scene.draw()
    #
    #             cam.position.xyz = orig_cam_position

    def on_draw(self):

        if self.current_vr_scene:
            with self.shader:
                rc.experimental.draw_vr_anaglyph(self.cube_fbo, self.current_vr_scene, self.active_scene, eye_poses=(.035, -.035))
                # rc.experimental.draw_vr_polarized(self.cube_fbo, self.current_vr_scene, self.active_scene, eye_poses=(.035, -.035))


    def update(self, dt):
        """Update arena position and vr_scene's camera to match motive's Arena and Rat rigid bodies."""
        self.arena.position.xyz = self.arena_rb.position
        self.arena.rotation.xyzw = self.arena_rb.quaternion

        if self.current_vr_scene:
            if sum(self.rodent_rb.position) != 0:
                self.current_vr_scene.camera.position.xyz = self.rodent_rb.position
                self.current_vr_scene.camera.rotation.xyzw = self.rodent_rb.quaternion
                self.current_vr_scene.camera.update()
                self.current_vr_scene.camera.uniforms['playerPos'] = self.current_vr_scene.camera.position.xyz

    @property
    def vr_scenes(self):
        return tuple(self._vr_scenes)

    @vr_scenes.setter
    def vr_scenes(self, value):
        raise AttributeError(
            "RatcaveApp.vr_scenes can not be directly assigned.  Instead, use the RatcaveApp.add_vr_scene() method.")

    def register_vr_scene(self, scene, parent_to_arena=True, match_light_to_beamer=True, make_cube_camera=True,
                          face_culling=False):
        """appends a virtual scene to the app, making any changes to the arena needed to display it correctly.
        Will also make it the current vr_scene automatically.
        """
        if not isinstance(scene, rc.Scene):
            raise TypeError("scene must be a ratcave Scene instance.")

        if not self.vr_scenes:
            if self.arena.textures:
                self.orig_texture = self.arena.textures[0]
            self.arena.textures.append(self.cube_fbo.texture)

        if parent_to_arena:
            for mesh in scene.meshes:
                mesh.parent = self.arena

        if match_light_to_beamer:
            scene.light.position.xyz = self.active_scene.light.position.xyz

        if make_cube_camera:
            scene.camera.rotation = scene.camera.rotation.to_quaternion()
            scene.camera.projection.aspect = 1.
            scene.camera.projection.fov_y = 90.
            scene.camera.projection.z_near = .004
            scene.camera.projection.z_far = 3.

        if not face_culling:
            scene.gl_states.states = scene.gl_states.states[:-1]

        # if self.fps_mode:
            # scene.camera.projection.fov_y = 120

        self._vr_scenes.add(scene)
        self.current_vr_scene = scene

    @property
    def current_vr_scene(self):
        return self._current_vr_scene

    @current_vr_scene.setter
    def current_vr_scene(self, scene):
        if not isinstance(scene, (rc.Scene, type(None))):
            raise TypeError("current_vr_scene must be a ratcave.Scene or None")
        if isinstance(scene, type(None)):
            self._current_vr_scene = None
            if self.orig_texture:
                self.arena.texture = self.orig_texture
            return
        if scene not in self.vr_scenes:
            raise ValueError("scene not in vr_scenes.  Use RatcaveApp.register_vr_scene() to register the scene first.")
        self._current_vr_scene = scene

    def run(self):
        """Runs the application's event loop."""
        pyglet.app.run()
