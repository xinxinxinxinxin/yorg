'''In this module we define the Car classes.'''
from abc import ABCMeta
from direct.showbase.InputStateGlobal import inputState
from panda3d.bullet import BulletBoxShape, BulletVehicle, ZUp, \
    BulletRigidBodyNode
from panda3d.core import TransformState, AudioSound

from ya2.gameobject import Event, GameObjectMdt, Gfx, Logic, Phys, Audio


class _Phys(Phys):
    '''This class models the physics component of a car.'''

    collision_box_shape = (.6, 1.4, .5)  # meters
    collision_box_pos = (0, 0, .5)  # meters
    wheel_fr_pos = (.75, 1.05, .4)  # meters
    wheel_fr_radius = .3  # meters
    wheel_fl_pos = (-.75, 1.05, .4)  # meters
    wheel_fl_radius = .3  # meters
    wheel_rr_pos = (.75, -.8, .4)  # meters
    wheel_rr_radius = .35  # meters
    wheel_rl_pos = (-.75, -.8, .4)  # meters
    wheel_rl_radius = .35  # meters
    max_speed = 90.0  # Km/h
    mass = 900  # kilograms
    steering_min_speed = 40  # degrees
    steering_max_speed = 10  # degrees
    steering_clamp = 40  # degrees
    steering_inc = 120  # degrees per second
    steering_dec = 120  # degrees per second
    engine_acc_frc = 5000
    engine_dec_frc = -2000
    brake_frc = 100
    pitch_control = 0  # default 0
    suspension_compression = .8  # default .83; should be lower than damping
    suspension_damping = .88  # default .88; should be greater than compression
    max_suspension_force = 5000  # default 6000
    max_suspension_travel_cm = 500  # default 500
    skid_info = 1  # default 1
    suspension_stiffness = 20  # default 5.88; f1 car == 200
    wheels_damping_relaxation = 20  # overwrites suspension_damping
    wheels_damping_compression = 20  # overwrites suspension_compression
    friction_slip = 3.5  # default 10.5
    roll_influence = .4  # default .1

    def __init__(self, mdt):
        Phys.__init__(self, mdt)
        chassis_shape = BulletBoxShape(self.collision_box_shape)
        transform_state = TransformState.makePos(self.collision_box_pos)
        mdt.gfx.nodepath.node().addShape(chassis_shape, transform_state)
        mdt.gfx.nodepath.node().setMass(self.mass)
        mdt.gfx.nodepath.node().setDeactivationEnabled(False)
        eng.world_phys.attachRigidBody(mdt.gfx.nodepath.node())

        self.__vehicle = BulletVehicle(eng.world_phys, mdt.gfx.nodepath.node())
        self.__vehicle.setCoordinateSystem(ZUp)
        self.__vehicle.setPitchControl(self.pitch_control)
        tuning = self.__vehicle.getTuning()
        tuning.setSuspensionCompression(self.suspension_compression)
        tuning.setSuspensionDamping(self.suspension_damping)

        eng.world_phys.attachVehicle(self.__vehicle)

        wheels_info = [
            (self.wheel_fr_pos, True, mdt.gfx.front_right_wheel_np,
             self.wheel_fr_radius),
            (self.wheel_fl_pos, True, mdt.gfx.front_left_wheel_np,
             self.wheel_fl_radius),
            (self.wheel_rr_pos, False, mdt.gfx.rear_right_wheel_np,
             self.wheel_rr_radius),
            (self.wheel_rl_pos, False, mdt.gfx.rear_left_wheel_np,
             self.wheel_rl_radius)]
        map(lambda (pos, front, nodepath, radius):
            self.__add_wheel(pos, front, nodepath.node(), radius),
            wheels_info)

        #mdt.gfx.nodepath.node().setCcdMotionThreshold(1e-7)
        #mdt.gfx.nodepath.node().setCcdSweptSphereRadius(3.50)

    def __add_wheel(self, pos, front, node, radius):
        '''This method adds a wheel to the car.'''
        wheel = self.__vehicle.createWheel()
        wheel.setNode(node)
        wheel.setChassisConnectionPointCs(pos)
        wheel.setFrontWheel(front)
        wheel.setWheelDirectionCs((0, 0, -1))
        wheel.setWheelAxleCs((1, 0, 0))
        wheel.setWheelRadius(radius)
        wheel.setSuspensionStiffness(self.suspension_stiffness)
        wheel.setWheelsDampingRelaxation(self.wheels_damping_relaxation)
        wheel.setWheelsDampingCompression(self.wheels_damping_compression)
        wheel.setFrictionSlip(self.friction_slip)
        wheel.setRollInfluence(self.roll_influence)
        wheel.setMaxSuspensionForce(self.max_suspension_force)
        wheel.setMaxSuspensionTravelCm(self.max_suspension_travel_cm)
        wheel.setSkidInfo(self.skid_info)

    @property
    def speed(self):
        return self.__vehicle.getCurrentSpeedKmHour()

    def set_forces(self, eng_frc, brake_frc, steering):
        '''This callback method is invoked on each frame.'''
        self.__vehicle.setSteeringValue(steering, 0)
        self.__vehicle.setSteeringValue(steering, 1)
        self.__vehicle.applyEngineForce(eng_frc, 2)
        self.__vehicle.applyEngineForce(eng_frc, 3)
        self.__vehicle.setBrake(brake_frc, 2)
        self.__vehicle.setBrake(brake_frc, 3)

    def destroy(self):
        '''The destroyer.'''
        self.__vehicle.destroy()


class _Audio(Audio):

    def __init__(self, mdt):
        Audio.__init__(self, mdt)
        self.engine_sfx = loader.loadSfx('assets/sfx/engine.ogg')
        self.brake_sfx = loader.loadSfx('assets/sfx/brake.ogg')
        self.crash_sfx = loader.loadSfx('assets/sfx/crash.ogg')
        map(lambda sfx: sfx.set_loop(True), [self.engine_sfx, self.brake_sfx, self.crash_sfx])
        self.engine_sfx.play()

    def update(self, input_dct):
        if input_dct['reverse'] and self.mdt.phys.speed > 50.0 and \
                self.brake_sfx.status() != AudioSound.PLAYING:
            self.brake_sfx.play()
        if not input_dct['reverse'] or self.mdt.phys.speed < 50.0:
            self.brake_sfx.stop()
        speed_ratio = self.mdt.phys.speed / self.mdt.phys.max_speed
        self.engine_sfx.set_volume(max(.25, abs(speed_ratio)))


class _Event(Event):
    '''This class manages the events of the Car class.'''

    def __init__(self, mdt):
        Event.__init__(self, mdt)
        label_events = [('forward', 'arrow_up'),
                        ('left', 'arrow_left'),
                        ('reverse', 'z'),
                        ('right', 'arrow_right')]
        map(lambda (lab, evt): inputState.watchWithModifiers(lab, evt),
            label_events)
        self.accept('bullet-contact-added', self.on_collision)
        self.__last_wall_time = None
        self.__last_goal_time = None
        self.__last_slow_time = None

    def on_collision(self, node1, node2):
        if node2.getName() == 'Wall':
            self.__last_wall_time = globalClock.getFrameTime()
        if node2.getName() == 'Goal':
            self.__last_goal_time = globalClock.getFrameTime()
        if node2.getName() == 'Slow':
            self.__last_slow_time = globalClock.getFrameTime()

    def evt_OnFrame(self, evt):
        '''This callback method is invoked on each frame.'''
        input_dct = {
            'forward': inputState.isSet('forward'),
            'left': inputState.isSet('left'),
            'reverse': inputState.isSet('reverse'),
            'right': inputState.isSet('right')}
        self.mdt.logic.update(input_dct)
        self.mdt.audio.update(input_dct)
        if self.__last_wall_time and \
                globalClock.getFrameTime() - self.__last_wall_time > .05:
            self.__last_wall_time = None
            print 'wall'
        if self.__last_goal_time and \
                globalClock.getFrameTime() - self.__last_goal_time > .05:
            self.__last_goal_time = None
            print 'goal'
        if self.__last_slow_time and \
                globalClock.getFrameTime() - self.__last_slow_time > .05:
            self.__last_slow_time = None
            print 'slow'
        eng.camera.setPos(self.mdt.gfx.nodepath.getPos())


class _Gfx(Gfx):
    '''This class models the graphics component of a car.'''

    def __init__(self, mdt):
        Gfx.__init__(self, mdt)
        vehicle_node = BulletRigidBodyNode('Vehicle')
        self.nodepath = eng.world_np.attachNewNode(vehicle_node)

        self.chassis_np = eng.loader.loadModel('car/car')
        self.chassis_np.reparentTo(self.nodepath)
        self.chassis_np.setDepthOffset(-2)

        self.front_right_wheel_np = eng.loader.loadModel('car/frontwheel')
        self.front_right_wheel_np.reparentTo(eng.world_np)

        self.front_left_wheel_np = eng.loader.loadModel('car/frontwheel')
        self.front_left_wheel_np.reparentTo(eng.world_np)

        self.rear_right_wheel_np = eng.loader.loadModel('car/rearwheel')
        self.rear_right_wheel_np.reparentTo(eng.world_np)

        self.rear_left_wheel_np = eng.loader.loadModel('car/rearwheel')
        self.rear_left_wheel_np.reparentTo(eng.world_np)

    def destroy(self):
        '''The destroyer.'''
        meshes = [self.nodepath,
                  self.chassis_np,
                  self.front_right_wheel_np,
                  self.front_left_wheel_np,
                  self.rear_right_wheel_np,
                  self.rear_right_wheel_np]
        map(lambda mesh: mesh.destroy(), meshes)


class _Logic(Logic):
    '''This class manages the events of the Car class.'''

    def __init__(self, mdt):
        Logic.__init__(self, mdt)
        self.__steering = 0  # degrees

    def update(self, input_dct):
        '''This callback method is invoked on each frame.'''
        eng_frc = brake_frc = 0
        d_t = globalClock.getDt()
        steering_inc = d_t * self.mdt.phys.steering_inc
        steering_dec = d_t * self.mdt.phys.steering_dec

        speed_ratio = min(1.0, self.mdt.phys.speed / self.mdt.phys.max_speed)
        steering_range = self.mdt.phys.steering_min_speed - self.mdt.phys.steering_max_speed
        steering_clamp = self.mdt.phys.steering_min_speed - speed_ratio * steering_range

        if input_dct['forward']:
            eng_frc = self.mdt.phys.engine_acc_frc if self.mdt.phys.speed < self.mdt.phys.max_speed else 0
            brake_frc = 0

        if input_dct['reverse']:
            eng_frc = self.mdt.phys.engine_dec_frc if self.mdt.phys.speed < .05 else 0
            brake_frc = self.mdt.phys.brake_frc

        if input_dct['left']:
            self.__steering += steering_inc
            self.__steering = min(self.__steering, steering_clamp)

        if input_dct['right']:
            self.__steering -= steering_inc
            self.__steering = max(self.__steering, -steering_clamp)

        if not input_dct['left'] and not input_dct['right']:
            if abs(self.__steering) <= steering_dec:
                self.__steering = 0
            else:
                steering_sign = (-1 if self.__steering > 0 else 1)
                self.__steering += steering_sign * steering_dec

        self.mdt.phys.set_forces(eng_frc, brake_frc, self.__steering)


class Car(GameObjectMdt):
    '''The Car class models a car.'''
    __metaclass__ = ABCMeta
    gfx_cls = _Gfx
    phys_cls = _Phys
    event_cls = _Event
    logic_cls = _Logic
    audio_cls = _Audio

    def __init__(self, pos, hpr):
        GameObjectMdt.__init__(self)
        self.gfx.nodepath.set_pos(pos)
        self.gfx.nodepath.set_hpr(hpr)
