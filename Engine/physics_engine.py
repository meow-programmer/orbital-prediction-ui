import math

class PhysicsEngine:
    def __init__(self, r, v, mass, dt):
        self.r = r[:]    # km
        self.v = v[:]    # km/s
        self.a = [0.0, 0.0]
        self.mass = mass
        self.dt = dt

    def step(self, time_scale, gravity, thrust, orientation_deg, is_thrusting):
        dt = self.dt * time_scale
    
        if is_thrusting and thrust > 0:
            angle = math.radians(orientation_deg)
            ax_t = thrust * math.cos(angle)
            ay_t = thrust * math.sin(angle)
        else:
            ax_t = ay_t = 0.0
    
        ax = gravity[0] + ax_t
        ay = gravity[1] + ay_t
    
        self.a = [ax, ay]
    
        self.v[0] += ax * dt
        self.v[1] += ay * dt
    
        self.r[0] += self.v[0] * dt
        self.r[1] += self.v[1] * dt
    