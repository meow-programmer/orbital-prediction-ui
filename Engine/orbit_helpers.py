import math
from PyQt5.QtCore import QPointF

def compute_predicted_orbit(window, steps=500, dt_sim=1.0):
    pred_points = []
    x, y = window.r
    vx, vy = window.v
    planet_masses = {"Earth": 5.972e24, "Moon": 7.347e22, "Mars": 6.39e23}
    M = planet_masses.get(window.selected_planet, 5.972e24)
    G = 6.67430e-20
    for _ in range(steps):
        r_dist = math.sqrt(x*x + y*y)
        if r_dist == 0: break
        a_grav = -G * M / (r_dist*r_dist)
        ax = a_grav * (x / r_dist)
        ay = a_grav * (y / r_dist)
        vx += ax * dt_sim
        vy += ay * dt_sim
        x += vx * dt_sim
        y += vy * dt_sim
        cx, cy = window.compute_center()
        pred_points.append(QPointF(cx + x * window.km_to_px, cy - y * window.km_to_px))
        if r_dist < window.planet_real_radius_km: break
    return pred_points

def apply_start_altitude(window):
    try:
        alt_km = float(window.positionInput.text().strip())
        r0_km = window.planet_real_radius_km + alt_km
        planet_masses = {"Earth": 5.972e24, "Moon": 7.347e22, "Mars": 6.39e23}
        M = planet_masses.get(window.selected_planet, 5.972e24)
        G = 6.67430e-20
        v_circ = math.sqrt(G * M / r0_km)
        window.r = [r0_km, 0.0]
        window.v = [0.0, v_circ]
        window.path_points.clear()
        # sync engine
        window.engine.r = window.r[:]
        window.engine.v = window.v[:]
        window.engine.a = [0.0, 0.0]
        window.update()
    except Exception:
        pass


def update_orbit_physics(window):
    # thrust
    if window.is_thrusting:
        angle_rad = math.radians(window.orientation_deg)
        thrust_acc = window.thrust / window.engine.mass
        ax = math.cos(angle_rad) * thrust_acc
        ay = -math.sin(angle_rad) * thrust_acc
    else:
        ax = ay = 0
    window.engine.apply_thrust(ax, ay)
    pos, vel = window.engine.step()
    window.ship_x = pos[0]*window.km_to_px + window.compute_center()[0]
    window.ship_y = pos[1]*window.km_to_px + window.compute_center()[1]
    window.path_points.append(QPointF(window.ship_x, window.ship_y))
    r_dist = math.sqrt(pos[0]**2 + pos[1]**2)
    speed_mag = math.sqrt(vel[0]**2 + vel[1]**2)
    window.livePosLabel.setText(f"Distance: {r_dist:.1f} km | Thrust: {window.thrust}")
    window.liveSpeedLabel.setText(f"Speed: {speed_mag:.3f} km/s")
    window.update()

def reset_starship_orbit(window):
    cx, cy = window.compute_center()
    r0_px = (window.planet_radius + window.orbit_radius)
    r0_km = r0_px / window.km_to_px
    planet_masses = {"Earth": 5.972e24, "Moon": 7.347e22, "Mars": 6.39e23}
    M = planet_masses.get(window.selected_planet, 5.972e24)
    G = 6.67430e-20
    if r0_km <= 0:
        r0_km = window.planet_real_radius_km + 200
    v_circ = math.sqrt(G * M / r0_km)
    window.r = [r0_km, 0.0]
    window.v = [0.0, v_circ]
    window.a = [0.0, 0.0]

