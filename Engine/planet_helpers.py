from PyQt5.QtGui import QColor
import math

def set_planet_params(window, name):
    name_lower = name.lower()
    window.selected_planet = name.title()
    if name_lower == 'earth':
        window.planet_real_radius_km = 6371
        window.planet_color = QColor(90, 150, 255)
    elif name_lower == 'mars':
        window.planet_real_radius_km = 3390
        window.planet_color = QColor(210, 120, 80)
    elif name_lower in ('moon', 'luna'):
        window.planet_real_radius_km = 1737
        window.planet_color = QColor(190, 190, 190)
    else:
        return
    window.planet_radius = max(2, int(round(window.planet_real_radius_km * window.km_to_px)))
    window.orbit_radius = 120 + (window.planet_radius // 5)
    window.btn6.setText(f"Planet: {name.title()}")
    window.planetOptions.setVisible(False)

def reset_starship_planet(window):
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
    # sync engine
    window.engine.r = window.r[:]
    window.engine.v = window.v[:]
    window.engine.a = [0.0, 0.0]

def get_planet_data(name):
    """Return a dict with real radius (km) and color for a planet name."""
    name_lower = name.lower()
    if name_lower == 'earth':
        return {"radius_km": 6371, "color": QColor(90, 150, 255)}
    elif name_lower == 'mars':
        return {"radius_km": 3390, "color": QColor(210, 120, 80)}
    elif name_lower in ('moon', 'luna'):
        return {"radius_km": 1737, "color": QColor(190, 190, 190)}
    else:
        return None

def apply_planet(window, name):
    """Set planet parameters and reset starship."""
    data = get_planet_data(name)
    if data is None:
        return
    
    window.selected_planet = name.title()
    window.planet_real_radius_km = data["radius_km"]
    window.planet_color = data["color"]
    window.planet_radius = max(2, int(round(data["radius_km"] * window.km_to_px)))
    window.orbit_radius = 120 + (window.planet_radius // 5)
    
    # reset starship position for new planet
    window.resetStarshipPosition()

