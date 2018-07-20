from __future__ import print_function

from app import motive, RatcaveApp
import ratcave as rc
import cfg
import pyglet
import events
import subprocess
from psychopy.gui import DlgFromDict
import sys
from datetime import datetime
from utils import create_and_configure_experiment_logs
#from pypixxlib import propixx (FIX ME! (If you want))



# Show User-Defined Experiment Settings
conditions = {'MOUSE': cfg.MOUSE,
              'EXPERIMENTER': cfg.EXPERIMENTER,
              'VR_WALL_X_OFFSET': cfg.VR_WALL_X_OFFSET,
              'PAPER_LOG_CODE': cfg.PAPER_LOG_CODE,
              'FIRST_PERSON_MODE': cfg.FIRST_PERSON_MODE
              }

dlg = DlgFromDict(conditions, title='{} Experiment Settings'.format(cfg.VR_WALL_EXPERIMENT_NAME),
                  order=['MOUSE', 'VR_WALL_X_OFFSET', 'EXPERIMENTER', 'PAPER_LOG_CODE', 'FIRST_PERSON_MODE'])
if dlg.OK:
    # log_code = dlg.dictionary['PAPER_LOG_CODE']
    # if not dlg.dictionary['RAT'].lower() in ['test', 'demo']:
        # if len(log_code) != 7 or log_code[3] != '-':
            # raise ValueError("Invalid PAPER_LOG_CODE.  Please try again.")
        # dlg.dictionary['PAPER_LOG_CODE'] = log_code.upper()

    dlg.dictionary['EXPERIMENT'] = cfg.VR_WALL_EXPERIMENT_NAME
    cfg.__dict__.update(dlg.dictionary)
else:
    sys.exit()


# Set Projector Settings (will have to do manually until you fix this!)
# projector = propixx.PROPixx()
# projector.setSleepMode(not cfg.PROJECTOR_TURNED_ON)
# projector.setLampLED(cfg.PROJECTOR_LED_ON)

# proj_brightness = cfg.VR_WALL_PROJECTOR_LED_INTENSITY if not 'demo' in cfg.RAT.lower() else "100.0"
# projector.setLedIntensity(proj_brightness)

# Create Virtual Scenes

# Create Virtual Scenes
vr_lighting = {
    'diffuse': cfg.VR_WALL_LIGHTING_DIFFUSE,
    'specular': cfg.VR_WALL_LIGHTING_SPECULAR,
    'ambient': cfg.VR_WALL_LIGHTING_AMBIENT,
    'flat_shading': cfg.VR_WALL_LIGHTING_FLAT_SHADING,
}


vr_arena = rc.WavefrontReader(cfg.ARENA_FILENAME).get_mesh(cfg.ARENA_MESH_NAME)

# vr_arena.texture = cfg.ARENA_LIGHTING_TEXTURE  was to changed in:
texture = rc.Texture.from_image(cfg.ARENA_LIGHTING_TEXTURE)  
vr_arena.textures.append(texture)

for key, value in vr_lighting.iteritems():
    vr_arena.uniforms[key] = value #.update(vr_lighting)

vr_wall = rc.WavefrontReader(cfg.VR_WALL_FILENAME).get_mesh(cfg.VR_WALL_MESHNAME)
vr_wall.position.xyz = cfg.VR_WALL_X_OFFSET, cfg.VR_WALL_Y_OFFSET, 0.

for key, value in vr_lighting.iteritems():
    vr_wall.uniforms[key] = value
vr_wall.textures.append(texture)

# (Future code) vr_all.textures.append(rc.Texture.from_image('myimage.png'))

vr_scene_with_wall = rc.Scene(meshes=[vr_arena, vr_wall], name="Arena with Wall", bgColor=[1., 1., 0.])
vr_scene_without_wall = rc.Scene(meshes=[vr_arena], name="Arena without Wall")


# Configure Ratcave App and register the virtual Scenes.
app = RatcaveApp(arena_objfile=cfg.ARENA_FILENAME, projector_file=cfg.PROJECTOR_FILENAME,
                 fullscreen=cfg.FULLSCREEN, screen=cfg.SCREEN, antialiasing=cfg.ANTIALIASING,
                 fps_mode=cfg.FIRST_PERSON_MODE)
app.set_mouse_visible(cfg.MOUSE_CURSOR_VISIBLE)
# app.arena.uniforms['diffuse'] = 0., 0., 0.
app.register_vr_scene(vr_scene_with_wall)
app.register_vr_scene(vr_scene_without_wall)

app.current_vr_scene = None #vr_scene_with_wall


# Build experiment event sequence
seq = []
if not cfg.MOUSE.lower() in ['test', 'demo']:
    motive_seq = [
        events.change_scene_background_color(scene=app.active_scene, color=(0., 0., 1.)),
        events.wait_for_recording(motive_client=motive),
        # events.change_scene_background_color(scene=app.active_scene, color=(0., 1., 0.)),
        # events.wait_for_distance_under(rb1=app.arena_rb, rb2=motive.rigid_bodies['TransportBox'], distance=0.5),
        # events.wait_for_distance_exceeded(rb1=app.rodent_rb, rb2=motive.rigid_bodies['TransportBox'], distance=0.4),
        events.change_scene_background_color(scene=app.active_scene, color=(1., 0., 0.)),
    ]
    seq.extend(motive_seq)
elif cfg.MOUSE.lower() in 'test':
    cfg.VR_WALL_PHASE_1_DURATION_SECS = 1.
    cfg.VR_WALL_PHASE_2_DURATION_SECS = 1.
    cfg.VR_WALL_PHASE_3_DURATION_SECS = 5.
    cfg.VR_WALL_PHASE_4_DURATION_SECS = 1.
else:
    cfg.VR_WALL_PHASE_1_DURATION_SECS = 1.
    cfg.VR_WALL_PHASE_2_DURATION_SECS = 1.
    cfg.VR_WALL_PHASE_3_DURATION_SECS = 50000.
    cfg.VR_WALL_PHASE_4_DURATION_SECS = 1.

exp_seq = [
    events.wait_duration(duration=cfg.VR_WALL_PHASE_1_DURATION_SECS),
    events.fade_to_black(meshes=[app.arena], speed=cfg.VR_WALL_FADE_SPEED),
    events.set_scene_to(app=app, new_scene=vr_scene_without_wall),
    events.fade_to_white(meshes=[app.arena], speed=cfg.VR_WALL_FADE_SPEED),
	
    events.wait_duration(duration=cfg.VR_WALL_PHASE_2_DURATION_SECS),
    events.fade_to_black(meshes=[app.arena], speed=cfg.VR_WALL_FADE_SPEED),
    events.set_scene_to(app=app, new_scene=vr_scene_with_wall),
    events.fade_to_white(meshes=[app.arena], speed=cfg.VR_WALL_FADE_SPEED),
	
    events.wait_duration(duration=cfg.VR_WALL_PHASE_3_DURATION_SECS),
    events.fade_to_black(meshes=[app.arena], speed=cfg.VR_WALL_FADE_SPEED),
    events.set_scene_to(app=app, new_scene=vr_scene_without_wall),
    events.fade_to_white(meshes=[app.arena], speed=cfg.VR_WALL_FADE_SPEED),
	
    events.wait_duration(duration=cfg.VR_WALL_PHASE_4_DURATION_SECS),
    events.fade_to_black(meshes=[app.arena], speed=cfg.VR_WALL_FADE_SPEED),
	
    events.close_app(app=app)
]
seq.extend(exp_seq)


# Make logfiles and set filenames
if cfg.MOUSE.lower() not in ['demo']:
    now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = '{expname}_{datetime}_{MOUSE}_{VR_WALL_X_OFFSET}_{person}_{log_code}'.format(
        expname=cfg.VR_WALL_EXPERIMENT_NAME, datetime=now, MOUSE=cfg.MOUSE,
        VR_WALL_X_OFFSET=cfg.VR_WALL_X_OFFSET, person=cfg.EXPERIMENTER[0].upper(),
        log_code=cfg.PAPER_LOG_CODE)
    create_and_configure_experiment_logs(filename=filename, motive_client=motive,
                                               exclude_subnames=['OBJECT', 'CLIFF', 'SPATIAL_NOVELTY', 'ACUITY'])


exp = events.chain_events(seq, log=True, motive_client=motive)
exp.next()
pyglet.clock.schedule(exp.send)

#app.current_vr_scene = vr_scene_with_wall

# Schedule the event sequence and run the VR App!
app.run()