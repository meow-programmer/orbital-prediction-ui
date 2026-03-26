import sys
import math
import copy
from physics_engine import PhysicsEngine
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QMenu, QLabel, QSlider, QFrame, QCheckBox, QLineEdit, QAction
from PyQt5.QtGui import QPainter, QColor, QBrush, QPalette, QPolygonF
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from orbit_helpers import apply_start_altitude, update_orbit_physics, compute_predicted_orbit, reset_starship_orbit
from planet_helpers import apply_planet, reset_starship_planet
from ui_helpers import updateButtonPositions, setPlanet, world_to_screen
PLANET_MU = {
    "Earth": 398600.4418,    # km^3 / s^2
    "Moon":  4902.800066,   # km^3 / s^2
    "Mars":  42828.375214   # km^3 / s^2
}

KARMAN_ALTITUDE_KM = {
    "Earth": 100,
    "Mars": 80,
    "Moon": 0     # Moon has no atmosphere, optional
}

LEO_ALTITUDE_KM = {
    "Earth": 400,
    "Mars": 250,
    "Moon": 100
}

# Physics behavior thresholds
PHYSICS_LEO_ALT = {
    "Earth": 160,   # km — anything above this can orbit freely
    "Moon": 100,
    "Mars": 120
}

PHYSICS_KARMAN_ALT = {
    "Earth": 100,  # km — above this, you are officially in space
    "Moon": 0,
    "Mars": 80
}

# Unified reference altitudes (km)
REFERENCE_ALTITUDES = {
    "Earth": {"karman": 100, "leo": 400},
    "Mars":  {"karman": 80,  "leo": 250},
    "Moon":  {"karman": 0,   "leo": 100}
}


VISUAL_KARMAN_ALT = 200   # you can tweak this freely
VISUAL_LEO_ALT = 400      # you can tweak this freely

class SpaceWindowUI(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_planet = "Earth"  # for gravity lookup
        self.initUI()
        self.time_scale = 1.0  # default 1× speed
        # Example: starting in a low circular orbit
        self.engine = PhysicsEngine(
            r=[0, 6771],     # km from Earth's center (6371 + 400)
            v=[7.67, 0],     # km/s circular velocity
            mass=100000,     # pick your spacecraft mass
            dt=0.1           # physics time step (fine-grained)
        )
        self.world_to_screen = lambda x, y: world_to_screen(self, x, y)
        self.resetStarshipPosition = lambda: reset_starship_orbit(self)
        self.updateButtonPositions = lambda: updateButtonPositions(self)

        self.orbit_visual_scale = 5.0  # scale small reference orbits for visibility
        self.zoom_factor = 1.0  # 1.0 = default view, >1 = zoom in, <1 = zoom out

        self.dragging_map = False
        self.last_mouse_pos = None

        self.setMouseTracking(True)
        self.predicted_path_points = []
        self.path_points = []
        self.angular_velocity = 0.0  # optional, for smooth turning
        self.max_turn_rate = 5.0     # degrees per tick
        # auto correction and thrust
        self.auto_state = "IDLE"   # IDLE | ORIENT | BURN | COAST
        self.hold_angle = None    # degrees
        self.burn_timer = 0.0
        self.enable_auto_correction = False
        self.max_turn_rate_deg = 2.0      # degrees per frame
        self.velocity_tolerance = 0.01
        self.is_thrusting = False
        self.thrust = 0.0
        # position offset for the whole system (change these to move planet+orbit)
        self.offset_x = 300
        self.offset_y = 200
        self.sim_running = False
        # orbit state
        self.orbit_angle = 0.0        # degrees
        self.angular_speed_deg = 1.0 # degrees per timer tick
        self.orbit_radius = 200
        # orbit target & lock detection
        self.orbit_target_alt = None   # km (target altitude for "set orbit")
        self.orbit_target_v = None     # km/s (target circular speed)
        self.orbit_locked = False
        self.orbit_lock_counter = 0
        # create timer once and set a sane default interval (16 ms ~ 60Hz)
        self.timer = QTimer()
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.updateOrbit)
        self.currentPlanet = "Earth"
        # planet logical coords (used as center offset before applying self.offset_*)
        self.planet_x = 350
        self.planet_y = 175
        self.ship_radius = 6
        # orientation
        self.ship_angle = 90.0   # degrees, -90 so it initially points "up"
        self.rotation_speed = 120.0  # degrees per second
        self.rotating_left = False
        self.rotating_right = False
        # scaling (visual)
        self.km_to_px = 40.0/6371.0
        self.zoom = self.km_to_px        
        self.planet_real_radius_km = 6371
        self.planet_radius = int(self.planet_real_radius_km * self.zoom * self.zoom_factor)  # <--- store as self
        self.planet_color = QColor(90, 150, 255)
     
        # absolute ship coordinates (will be computed by resetStarshipPosition)
        self.ship_x = 0
        self.ship_y = 0
        # place ship initially (absolute coordinates)
        self.resetStarshipPosition()
        self.recompute_prediction()
        pass

    def _apply_start_alt(self):
        apply_start_altitude(self)
        self.update()


    def initUI(self):
        self.setWindowTitle("Spaceflight orbital analysis and position prediction")
        self.resize(1400,800)
        ##### BUTTONS #####
        self.btn1 = QPushButton('Enter starting position', self)
        self.btn1.resize(200,50)
        self.positionBox = QFrame(self)
        self.positionBox.setStyleSheet("background: #e8e8e8; border: 1px solid #bbbbbb;")
        self.positionBox.setVisible(False)
        self.positionBox.resize(200,50)
        self.positionInput = QLineEdit(self.positionBox)
        self.positionInput.setPlaceholderText("Enter current position of starship (alt km)")
        self.positionInput.resize(180,30)
        self.positionInput.move(10,10)
        # apply altitude on Enter
        self.positionInput.returnPressed.connect(self._apply_start_alt)
        self.btn1.clicked.connect(self.togglePositionBox)
        self.btn2 = QPushButton('Enter ending satellite position', self)
        self.btn2.resize(200,50)
        self.destBox = QFrame(self)
        self.destBox.setStyleSheet("background: #e8e8e8; border: 1px solid #bbbbbb;")
        self.destBox.setVisible(False)
        self.destBox.resize(200, 50)
        
        self.destInput = QLineEdit(self.destBox)
        self.destInput.setPlaceholderText("Enter ending satellite position")
        self.destInput.resize(180, 30)
        self.destInput.move(10, 10)
        
        self.btn2.clicked.connect(self.toggleDestinationPosition)
        self.destInput.returnPressed.connect(self.apply_destination_position)

        self.btn3 = QPushButton('Choose propulsion type', self)
        self.btn3.resize(200,50)
        self.propulsionOptions = QFrame(self)
        self.propulsionOptions.setStyleSheet("background: #e8e8e8; border: 1px solid #bbbbbb;")
        self.propulsionOptions.setVisible(False)
        self.propulsionOptions.resize(200, 120)
        
        self.propBtn1 = QPushButton("Chemical rocket", self.propulsionOptions)
        self.propBtn1.resize(200, 40)
        self.propBtn1.move(0, 0)
        
        self.propBtn2 = QPushButton("Ion drive", self.propulsionOptions)
        self.propBtn2.resize(200, 40)
        self.propBtn2.move(0, 40)
        
        self.propBtn3 = QPushButton("Nuclear thermal", self.propulsionOptions)
        self.propBtn3.resize(200, 40)
        self.propBtn3.move(0, 80)
        
        self.btn3.clicked.connect(self.togglePropulsionList)
        self.btn4 = QPushButton('Enter mass of spaceship', self)
        self.btn4.resize(200,50)
        self.massBox = QFrame(self)
        self.massBox.setStyleSheet("background: #e8e8e8; border:1px solid #bbbbbb;")
        self.massBox.setVisible(False)
        self.massBox.resize(200,50)
        self.massInput = QLineEdit(self.massBox)
        self.massInput.setPlaceholderText("Enter mass (kg)")
        self.massInput.resize(180,30)
        self.massInput.move(10,10)
        self.btn4.clicked.connect(self.toggleMassBox)
        self.btn5 = QPushButton('Enter fuel', self)
        self.btn5.resize(200,50)
        self.fuelBox = QFrame(self)
        self.fuelBox.setStyleSheet("background: #e8e8e8; border:1px solid #bbbbbb;")
        self.fuelBox.setVisible(False)
        self.fuelBox.resize(200,50)
        self.fuelInput = QLineEdit(self.fuelBox)
        self.fuelInput.setPlaceholderText("Enter fuel (L)")
        self.fuelInput.resize(180,30)
        self.fuelInput.move(10,10)
        self.btn5.clicked.connect(self.toggleFuelBox)
        # Create the button
        self.btn6 = QPushButton('Enter planet', self)
        self.btn6.resize(200,50)
        
        # Create a small black arrow label on the right end
        self.arrowLabel = QLabel("▼", self.btn6)
        self.arrowLabel.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.arrowLabel.setStyleSheet("color: black; font-size: 10px;")  # small black arrow
        self.arrowLabel.adjustSize()
        # Position it on the right side of the button
        self.arrowLabel.move(self.btn6.width() - self.arrowLabel.width() - 10, 
                            (self.btn6.height() - self.arrowLabel.height()) // 2)
        
        self.planetOptions = QFrame(self)
        self.planetOptions.setStyleSheet("background: #e8e8e8; border: 1px solid #bbbbbb;")
        self.planetOptions.setVisible(False)
        self.planetOptions.resize(200,120)
        
        self.planetBtn1 = QPushButton("Earth", self.planetOptions)
        self.planetBtn1.resize(200,40)
        self.planetBtn1.move(0,0)
        
        self.planetBtn2 = QPushButton("Moon", self.planetOptions)
        self.planetBtn2.resize(200,40)
        self.planetBtn2.move(0,40)
        
        self.planetBtn3 = QPushButton("Mars", self.planetOptions)
        self.planetBtn3.resize(200,40)
        self.planetBtn3.move(0,80)
        self.planetBtn1.clicked.connect(lambda: self.setPlanet('Earth'))
        self.planetBtn2.clicked.connect(lambda: self.setPlanet('Moon'))
        self.planetBtn3.clicked.connect(lambda: self.setPlanet('Mars'))        
        self.btn6.clicked.connect(self.togglePlanetList)
        self.btn7 = QPushButton('Simulation speed', self)
        self.btn7.resize(200,50)
        # Label that shows current speed
        self.simspeedlabel = QLabel("1x", self)
        self.simspeedlabel.setStyleSheet("background-color: rgba(0,0,0,170); color: white; padding: 4px; border-radius: 4px;")
        self.simspeedlabel.adjustSize()
        self.simspeedlabel.show()
        
        menu = QMenu(self)
        self.btn7.setMenu(menu)
        
        self.action_x1 = QAction("1x", self)
        self.action_x2 = QAction("2x", self)
        self.action_x5 = QAction("5x", self)
        self.action_x10 = QAction("10x", self)
        self.action_x50 = QAction("50x", self)
        self.action_max = QAction("Max", self)
        
        menu.addAction(self.action_x1)
        menu.addAction(self.action_x2)
        menu.addAction(self.action_x5)
        menu.addAction(self.action_x10)
        menu.addAction(self.action_x50)  
        menu.addAction(self.action_max)
        
        # make sure clicking an action updates both speed multiplier and the label
        self.action_x1.triggered.connect(lambda: self.setSimulationSpeed(1))
        self.action_x2.triggered.connect(lambda: self.setSimulationSpeed(2))
        self.action_x5.triggered.connect(lambda: self.setSimulationSpeed(5)) 
        self.action_x10.triggered.connect(lambda: self.setSimulationSpeed(10))
        self.action_x50.triggered.connect(lambda: self.setSimulationSpeed(50))
        self.action_max.triggered.connect(lambda: self.setSimulationSpeed(100))
        self.btn8 = QPushButton('Start simulation', self)
        self.btn8.resize(200,50)
        self.btn8.clicked.connect(self.startOrbit)
        # LIVE SPEED LABEL
        self.liveSpeedLabel = QLabel("Speed: 0 km/s", self)
        self.liveSpeedLabel.setStyleSheet(
            "font-size: 13px; color: white; background-color: rgba(0,0,0,140); padding:4px; border-radius:4px;"
        )
        self.liveSpeedLabel.adjustSize()
        self.liveSpeedLabel.show()
        self.liveSpeedLabel.raise_()  # ensure it's above custom painting

        # Instruction label that guides user to set the orbit and shows completion
        self.instructionLabel = QLabel("", self)
        self.instructionLabel.setStyleSheet(
            "font-size: 13px; color: black; background-color: rgba(255,255,255,220); padding:6px; border-radius:6px;"
        )
        self.instructionLabel.setWordWrap(True)
        self.instructionLabel.setVisible(False)
        self.instructionLabel.adjustSize()
        
        ##### TOGGLE SWITCH #####
        self.toggle = QCheckBox(self)
        self.toggle.setText("Auto-correction")
        self.toggle.resize(200,50)
        self.toggle.stateChanged.connect(self.toggle_auto_correct)
        
        # Apply a simple toggle-style stylesheet
        self.toggle.setStyleSheet("""
            QCheckBox::indicator {
                width: 40px;
                height: 20px;
                border-radius: 10px;
                background: red;
            }
            QCheckBox::indicator:checked {
                background: green;
            }
        """)
        # LIVE POSITION LABEL (child of this widget)
        self.livePosLabel = QLabel("Distance: 0 px", self)   # parent=self (important)
        # make it readable regardless of background and keep it compact
        self.livePosLabel.setStyleSheet(
            "font-size: 13px; color: white; background-color: rgba(0,0,0,140); padding:4px; border-radius:4px;"
        )
        self.livePosLabel.adjustSize()
        # we will position it properly in updateButtonPositions()
        self.livePosLabel.show()
        self.livePosLabel.raise_()   # ensure it's above the custom painting
        ##### SLIDER #####
        self.sliderBox = QFrame(self)
        self.sliderBox.setFrameShape(QFrame.StyledPanel)
        self.sliderBox.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 2px solid #cccccc;
                border-radius: 10px;
            }
        """)
        self.sliderBox.setGeometry(50, 450, 400, 130)
        self.slider = QSlider(Qt.Horizontal, self.sliderBox)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setValue(0)
        self.slider.resize(300,40)
        self.slider.move(150, 40)   # <--- center it nicely inside the box
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setSingleStep(1)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #dcdcdc;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid #4a90e2;
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::sub-page:horizontal {
                background: #4a90e2;
                border-radius: 4px;
            }
        """)
        
        self.label0 = QLabel("0", self.sliderBox)
        self.label1 = QLabel("50", self.sliderBox)
        self.label2 = QLabel("100", self.sliderBox)
        
        self.positionSliderLabels()          
        
        self.sliderTitle = QLabel("Thrust override (manual control)", self.sliderBox)
        self.sliderTitle.setStyleSheet("font-weight: bold;")
        self.sliderTitle.adjustSize()
        self.sliderTitle.move(
            (self.sliderBox.width() - self.sliderTitle.width())//2, 20
        )
        self.state_label = QLabel(self)
        self.state_label.setStyleSheet(
            """
            background-color: rgba(0,0,0,170);
            color: #ffffff;
            padding: 6px;
            border-radius: 6px;
            font-family: Consolas, monospace;
            font-size: 11px         
            """
        )
        self.state_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.state_label.move(20,20)
        self.state_label.setFixedWidth(240)
        self.state_label.setWordWrap(True)
        self.state_label.show()
        
        # In initUI() after creating slider
        # updateThrust will now also set self.is_thrusting when val > 0
        self.slider.valueChanged.connect(self.updateThrust)

        self.legendLabel = QLabel(self)
        self.legendLabel.setStyleSheet("""
            background-color: rgba(0,0,0,150);
            color: white;
            padding: 6px;
            border-radius: 6px;
            font-size: 11px;
        """)
        self.legendLabel.move(20, 20)
        self.legendLabel.setText("")
        self.legendLabel.show()
        self.legendLabel.move(10, 10)  # top-left corner (10 px margin)
        self.legendLabel.raise_()       # make sure it's above other widgets
        self.updateLegend()



    def updateLegend(self):
        k = KARMAN_ALTITUDE_KM.get(self.selected_planet, "—")
        leo = LEO_ALTITUDE_KM.get(self.selected_planet, "—")
    
        self.legendLabel.setText(
            f"Reference Orbits\n"
            f"• Kármán line: {k} km\n"
            f"• LEO: {leo} km"
        )
        self.legendLabel.adjustSize()

    def paintEvent(self, event):
        painter = QPainter(self)

        self.cx, self.cy = self.compute_center()
        
        # Draw reference orbits first
        self.draw_reference_orbits(painter)
    
        # Draw planet
        cx, cy = self.compute_center()
        planet_px = int(self.planet_real_radius_km * self.zoom * self.zoom_factor)
        painter.setBrush(self.planet_color)
        painter.drawEllipse(cx - planet_px, cy - planet_px, 2 * planet_px, 2 * planet_px)

        self.draw_starship(painter)
    
        painter.setPen(QColor(0, 255, 255, 160))  # cyan, semi-transparent
        for i in range(1, len(self.predicted_path_points)):
           x1, y1 = world_to_screen(self, *self.predicted_path_points[i-1])
           x2, y2 = world_to_screen(self, *self.predicted_path_points[i])
           painter.drawLine(x1, y1, x2, y2)

    
        # Draw actual path
        painter.setPen(QColor(255, 255, 0))
        for i in range(1, len(self.path_points)):
            x1, y1 = world_to_screen(self, *self.path_points[i-1])
            x2, y2 = world_to_screen(self, *self.path_points[i])
            painter.drawLine(x1, y1, x2, y2)

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120  # usually ±1 per notch
        self.zoom_factor *= 1.1 ** delta
        self.zoom_factor = max(0.1, min(self.zoom_factor, 10))  # clamp zoom
        self.update()
            
    def draw_reference_orbits(self, painter):
        # Only Earth has Kármán + LEO reference lines
        if self.selected_planet != "Earth":
            return
    
        cx, cy = self.compute_center()
        scale = self.zoom * self.zoom_factor
    
        karman_alt = REFERENCE_ALTITUDES["Earth"]["karman"]
        leo_alt    = REFERENCE_ALTITUDES["Earth"]["leo"]
    
        # Kármán line
        r_px = int((self.planet_real_radius_km + karman_alt) * scale)
        pen = painter.pen()
        pen.setColor(QColor(180, 180, 180, 120))
        pen.setStyle(Qt.DashLine)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(cx - r_px, cy - r_px, 2*r_px, 2*r_px)
    
        # LEO line
        r_px = int((self.planet_real_radius_km + leo_alt) * scale)
        pen.setColor(QColor(160, 160, 160, 180))
        pen.setStyle(Qt.DotLine)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(cx - r_px, cy - r_px, 2*r_px, 2*r_px)

    def compute_predicted_orbit(self, steps=500):
        self.predicted_path_points.clear()
    
        # clone real state
        rx, ry = self.engine.r
        vx, vy = self.engine.v
    
        mu = PLANET_MU[self.selected_planet]
        dt = 0.016 * self.time_scale
    
        for _ in range(steps):
            r = math.sqrt(rx*rx + ry*ry)
            if r == 0:
                break
    
            # SAME gravity as real ship
            ax = -mu * rx / (r**3)
            ay = -mu * ry / (r**3)
    
            # integrate
            vx += ax * dt
            vy += ay * dt
    
            rx += vx * dt
            ry += vy * dt
    
            # SAME world coordinates
            self.predicted_path_points.append((rx, ry))

    def recompute_prediction(self):
        self.compute_conic_orbit()
        self.update()

    def compute_orbital_elements(self):
        rx, ry = self.engine.r
        vx, vy = self.engine.v
        mu = PLANET_MU[self.selected_planet]
    
        r = math.hypot(rx, ry)
        v = math.hypot(vx, vy)
    
        # specific energy
        epsilon = v*v/2 - mu/r
        if abs(epsilon) < 1e-8:
            return None
    
        a = -mu / (2 * epsilon)
    
        # angular momentum
        h = rx * vy - ry * vx
    
        # eccentricity vector
        ex = (vy * h) / mu - rx / r
        ey = (-vx * h) / mu - ry / r
        e = math.hypot(ex, ey)
    
        rp = a * (1 - e)
        ra = a * (1 + e)
    
        return {
            "a": a,
            "e": e,
            "rp": rp,
            "ra": ra
        }


    def apply_auto_correction(self, dt):
        rx, ry = self.engine.r
        vx, vy = self.engine.v
    
        mu = PLANET_MU[self.selected_planet]
        r = math.hypot(rx, ry)
        if r == 0:
            return
    
        alt = r - self.planet_real_radius_km
        target_alt = self.orbit_target_alt
    
        # Target radius
        if target_alt is None:
            target_r = r
        else:
            target_r = self.planet_real_radius_km + target_alt
    
        # --- Tangential directions ---
        t1 = (-ry / r,  rx / r)
        t2 = ( ry / r, -rx / r)
        dot1 = vx * t1[0] + vy * t1[1]
        dot2 = vx * t2[0] + vy * t2[1]
        tx, ty = t1 if dot1 > dot2 else t2
    
        # Desired circular speed
        v_target = math.sqrt(mu / target_r)
    
        alt_error = r - target_r
        speed = math.hypot(vx, vy)

        # --- RADIAL VELOCITY (km/s) ---
        radial_v = (rx * vx + ry * vy) / r
    
        # --- ALTITUDE CHANGE PHASE ---
        if abs(alt_error) > 2.0:
            if target_r > r:
                # RAISING orbit → ONLY prograde thrust
                pass  # tx, ty already prograde
            else:
                # LOWERING orbit → ONLY retrograde thrust
                tx *= -1
                ty *= -1

    
        desired_angle = math.degrees(math.atan2(ty, tx))
    
                # --- ATTITUDE CONTROL ---
        if self.auto_state == "ORIENT":
            angle_diff = (self.hold_angle - self.ship_angle + 540) % 360 - 180
        
            if abs(angle_diff) > 1.0:
                turn = max(-self.max_turn_rate_deg,
                           min(self.max_turn_rate_deg, angle_diff))
                self.ship_angle = (self.ship_angle + turn) % 360
            else:
                # angle acquired → start burn
                self.auto_state = "BURN"
                self.burn_timer = 0.0
        
        if self.auto_state == "BURN":
            self.is_thrusting = True
            self.burn_timer += dt
        
            # short controlled burns (VERY IMPORTANT)
            if self.burn_timer > 0.5:
                self.is_thrusting = False
                self.auto_state = "COAST"

        elif self.auto_state == "COAST":
            self.is_thrusting = False
        
            # wait until next apsis
            if abs(radial_v) < 0.01:
                # recompute new burn direction
                desired_angle = math.degrees(math.atan2(ty, tx))
                self.hold_angle = desired_angle
                self.auto_state = "ORIENT"
        # else: do nothing → hold attitude

        if self.auto_state == "IDLE":
            if abs(alt_error) > 2.0:
                # altitude correction → prograde or retrograde
                direction = 1 if alt_error < 0 else -1
                tx *= direction
                ty *= direction
            else:
                # circularization
                pass
        
            self.hold_angle = math.degrees(math.atan2(ty, tx))
            self.auto_state = "ORIENT"

        # --- UI: MOVE THE SLIDER HERE ---
        if self.enable_auto_correction:
            self.slider.blockSignals(True)
            self.slider.setValue(60 if self.is_thrusting else 0)
            self.slider.blockSignals(False)


    def apply_destination_position(self):
        try:
            alt = float(self.destInput.text())
            self.orbit_target_alt = alt

            r = self.planet_real_radius_km + alt
            mu = PLANET_MU[self.selected_planet]
            self.orbit_target_v = math.sqrt(mu / r)

            self.orbit_locked = False
            self.orbit_lock_counter = 0
            self.instructionLabel.setText(
                f"Target orbit set: {alt:.0f} km\n"
                f"Target speed ≈ {self.orbit_target_v:.3f} km/s\n"
                f"Adjust thrust and orientation to match."
            )
            self.instructionLabel.adjustSize()
        
        except ValueError:
            pass

    def PressEvent(self, event):
        if event.key() == Qt.Key_A:
            self.orientation_deg -= self.max_turn_rate
        elif event.key() == Qt.Key_D:
            self.orientation_deg += self.max_turn_rate
        
        self.orientation_deg %= 360
        
        # Update predicted orbit
        
        super().keyPressEvent(event)

    def updateThrust(self, val):
        self.thrust = float(val)
    
        # ONLY allow manual thrust when auto-correction is OFF
        if not self.enable_auto_correction:
            self.is_thrusting = (val > 0)
    
        self.livePosLabel.setText(f"Thrust: {val}")


    def positionSliderLabels(self):
        slider_x = self.slider.x() 
        slider_y = self.slider.y()
        slider_w = self.slider.width()
        slider_h = self.slider.height()
    
        label_y = slider_y + slider_h + 10
    
        self.label0.adjustSize()
        self.label1.adjustSize()
        self.label2.adjustSize()
        
        half_slider = slider_x + slider_w // 2
        
        self.label0.move(int(slider_x - self.label0.width() // 2), int(label_y))
        self.label1.move(int(half_slider - self.label1.width() // 2), int(label_y))
        self.label2.move(int(slider_x + slider_w - self.label2.width() // 2), int(label_y))

    def togglePositionBox(self):
        self.positionBox.setVisible(not self.positionBox.isVisible())
        self.updateButtonPositions()

    def toggleDestinationPosition(self):
        self.destBox.setVisible(not self.destBox.isVisible())
        self.updateButtonPositions()

    def togglePropulsionList(self):
        self.propulsionOptions.setVisible(not self.propulsionOptions.isVisible())
        self.updateButtonPositions()

    def togglePlanetList(self):
        # place dropdown under the button each time so it doesn't drift
        if not self.planetOptions.isVisible():    
            x = self.btn6.x()
            y = self.btn6.y() + self.btn6.height()
            self.planetOptions.move(x, y)
        self.planetOptions.setVisible(not self.planetOptions.isVisible())
        # ensure layout is updated so that dropdown doesn't appear in the wrong place
        self.updateButtonPositions()

    def setPlanet(self, name):
        self.selected_planet = name
    
        # Update visuals (planet color, radius, etc.)
        apply_planet(self, name)  # <-- must not move the ship!
    
        # Only reset ship physics if sim is running
        if self.sim_running:
            reset_starship_planet(self)  # reset orbit/position for physics
    
        # Recompute predicted orbit so paths are updated
        self.recompute_prediction()
    
        # Update legend and repaint immediately
        self.updateLegend()
        self.update()



    
    def toggleMassBox(self):
        self.massBox.setVisible(not self.massBox.isVisible())
        self.updateButtonPositions()

    def toggleFuelBox(self):
        self.fuelBox.setVisible(not self.fuelBox.isVisible())
        self.updateButtonPositions()

    def setSimSpeed(self,text):
        # keep this method if you call it elsewhere; sync label
        self.simspeedlabel.setText(text)
        self.updateButtonPositions()

    def compute_center(self):
        """Return integer (center_x, center_y) for the planet (applies offsets)."""
        cx = self.offset_x + self.planet_x
        cy = self.offset_y + self.planet_y
        return int(cx), int(cy)
    
    def compute_conic_orbit(self, samples=360):
        self.predicted_path_points.clear()
    
        rx, ry = self.engine.r
        vx, vy = self.engine.v
        mu = PLANET_MU[self.selected_planet]
    
        r = math.hypot(rx, ry)
        v = math.hypot(vx, vy)
    
        # specific orbital energy
        epsilon = v*v/2 - mu/r
        if abs(epsilon) < 1e-8:
            return  # near-parabolic, skip
    
        a = -mu / (2 * epsilon)
    
        # angular momentum (scalar, 2D)
        h = rx * vy - ry * vx
    
        # eccentricity vector (CRITICAL FIX)
        ex = (vy * h) / mu - rx / r
        ey = (-vx * h) / mu - ry / r
        e = math.hypot(ex, ey)
    
        # argument of periapsis (CORRECT orientation)
        omega = math.atan2(ey, ex)
    
        for i in range(samples):
            theta = 2 * math.pi * i / samples
            r_theta = a * (1 - e*e) / (1 + e * math.cos(theta))
    
            x = r_theta * math.cos(theta + omega)
            y = r_theta * math.sin(theta + omega)
    
            self.predicted_path_points.append((x, y))


    
    ####### EVENT FUNCTIONS #######
    def resizeEvent(self, event):
        self.path_points.clear()
        self.updateButtonPositions()
        self.positionSliderLabels()
        self.offset_x = self.width() * 0.25
        self.offset_y = self.height() * 0.25
        self.resetStarshipPosition()
    
        # keep legend at top-left
        self.legendLabel.move(10, 10)
        self.legendLabel.raise_()
        super().resizeEvent(event)


    def toggle_auto_correct(self, state):
        self.enable_auto_correction = (state == Qt.Checked)
    
        if self.enable_auto_correction:
            self.auto_state = "IDLE"   # fresh start
            self.is_thrusting = False
        else:
            self.is_thrusting = False

    


    def setSimulationSpeed(self, multiplier):
        # speed multiplier for physics updates
        self.time_scale = multiplier
        # update label shown in UI
        try:
            self.simspeedlabel.setText(f"{multiplier}x")
            self.simspeedlabel.adjustSize()
        except Exception:
            pass
        # keep timer interval at a sane rendering rate; time_scale multiplies physics dt
        self.timer.setInterval(16)
    
        print(f"Simulation speed set to {multiplier}×")

    def updateOrbit(self):
        dt = 0.016  # ~60 FPS
        self.update_simulation(dt)

        if not self.sim_running:
            return
        
        gravity = self.compute_gravity_vector()  # returns [gx, gy]

    
        self.engine.step(   
            gravity=gravity,
            time_scale=self.time_scale,
            thrust=self.thrust * 1e-5,
            orientation_deg=self.ship_angle,
            is_thrusting=self.is_thrusting
        )

        elements = self.compute_orbital_elements()
        if elements:
            self.apoapsis = elements["ra"] - self.planet_real_radius_km
            self.periapsis = elements["rp"] - self.planet_real_radius_km
        
        if self.is_thrusting:
            self.recompute_prediction()
    
        self.ship_x, self.ship_y = self.engine.r
        self.path_points.append((self.ship_x, self.ship_y))
    
        # Calculate real altitude
        rx, ry = self.engine.r
        r = math.sqrt(rx**2 + ry**2)
        alt = r - self.planet_real_radius_km

        if self.enable_auto_correction:
            self.apply_auto_correction(dt)
    
        # Physics triggers
        planet_ref = REFERENCE_ALTITUDES[self.selected_planet]
        self.in_space   = alt >= planet_ref["karman"]
        self.orbit_free = alt >= planet_ref["leo"]
    
        # Example behavior changes
        if self.in_space:
            self.engine.drag_factor = 0.0  # no atmospheric drag
        else:
            self.engine.drag_factor = 0.001  # small drag below space
    
        if self.orbit_target_alt is None:
            self.enable_auto_correction = False

    
        # optional: update live labels
        self.livePosLabel.setText(f"Altitude: {alt:.1f} km")
        self.livePosLabel.adjustSize()

        vx, vy = self.engine.v
        speed = math.sqrt(vx*vx + vy*vy)

        self.liveSpeedLabel.setText(f"Speed: {speed:.3f} km/s")
        self.liveSpeedLabel.adjustSize()
        
        ##### debug mode #####
        vx, vy = self.engine.v
        vel_angle = math.degrees(math.atan2(vy, vx))
        
        print(f"Ship angle: {self.ship_angle:.1f}°, Velocity angle: {vel_angle:.1f}°")
        ##### debug mode #####

        self.update()

        # orbit lock detection: if target is set and not yet locked, check criteria
        if self.orbit_target_alt is not None and not self.orbit_locked:
            # radial velocity check
            rx, ry = self.engine.r
            vx, vy = self.engine.v
            r_now = math.sqrt(rx*rx + ry*ry)
            if r_now != 0:
                radial_v = (rx*vx + ry*vy) / r_now
            else:
                radial_v = 0.0

            # speed and altitude
            speed = math.sqrt(vx*vx + vy*vy)
            alt_diff = abs((r_now - self.planet_real_radius_km) - self.orbit_target_alt)

            if self.orbit_target_alt is not None and not self.orbit_locked:
                alt_error = alt - self.orbit_target_alt
                speed_error = speed - self.orbit_target_v

                guidance = []

                if abs(alt_error) > 2:
                    if alt_error < 0:
                        guidance.append("Lower orbit: reduce speed slightly.")
                    else:
                        guidance.append("Raise orbit: increase speed slightly.")

                if abs(speed_error) > 0.02:
                    if speed_error > 0:
                        guidance.append("Too fast: thrust retrograde")
                        
                    else:
                        guidance.append("Too slow: thrust prograde")

                vel_angle = math.degrees(math.atan2(vy, vx))
                angle_diff = (vel_angle - self.ship_angle + 540) % 360 - 180

                if abs(angle_diff) > 10:
                    guidance.append(
                        "Rotate" + ("right" if angle_diff > 0 else "left") +
                        " to align with velocity" 
                    )

                if guidance:
                    self.instructionLabel.setText(
                        f"Target orbit: {self.orbit_target_alt:.0f} km\n"+
                        "\n".join(guidance)
                    )
                    self.instructionLabel.adjustSize()
                    

            # tolerances
            alt_tol_km = 2.0
            radial_tol = max(0.02, 0.01 * speed)   # km/s
            speed_tol = max(0.02, 0.02 * (self.orbit_target_v or 1.0))

            if alt_diff <= alt_tol_km and abs(radial_v) <= radial_tol and abs(speed - (self.orbit_target_v or speed)) <= speed_tol:
                self.orbit_lock_counter += 1
            else:
                self.orbit_lock_counter = 0

            # require criteria hold for some consecutive updates (~1 second @60Hz)
            if self.orbit_lock_counter >= 60:
                self.orbit_locked = True
                self.instructionLabel.setText("Orbit complete.")
                self.instructionLabel.adjustSize()
                self.instructionLabel.setVisible(True)

    def compute_gravity_vector(self):
        # position relative to planet center (km)
        rx, ry = self.engine.r
        r = math.sqrt(rx*rx + ry*ry)
    
        if r == 0:
            return [0.0, 0.0]
    
        mu = PLANET_MU[self.selected_planet]
    
        factor = -mu / (r**3)
        return [
            factor * rx,
            factor * ry
        ]


    def mouseMoveEvent(self, event):
        margin = 12
        x = event.x() + 20
        y = event.y() + 20
        max_x = self.width() - self.state_label.width() - margin
        max_y = self.height() - self.state_label.height() - margin
        x = max(margin, min(int(x), int(max_x)))
        y = max(margin, min(int(y), int(max_y)))
        self.state_label.move(x,y)
        self.update_state_display()
        if self.dragging_map and self.last_mouse_pos is not None:
            delta = event.pos() - self.last_mouse_pos
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self.last_mouse_pos = event.pos()
            self.update()   

        margin = 12
        x = event.x() + 20
        y = event.y() + 20
        max_x = self.width() - self.state_label.width() - margin
        max_y = self.height() - self.state_label.height() - margin
        x = max(margin, min(int(x), int(max_x)))
        y = max(margin, min(int(y), int(max_y)))
        self.state_label.move(x,y)
        self.update_state_display() 
        super().mouseMoveEvent(event)

    def update_state_display(self):
        rx, ry = self.engine.r
        vx, vy = self.engine.v
        ax, ay = self.engine.a
        txt = (
            f"r (km) = ({rx:.1f}, {ry:.1f})\n"
            f"v (km/s) = ({vx:.3f}, {vy:.3f})\n"
            f"a (km/s²) = ({ax:.6f}, {ay:.6f})"
        )
        self.state_label.setText(txt)

    def draw_starship(self, painter):
        sx, sy = world_to_screen(self, self.ship_x, self.ship_y)
    
        painter.save()
        painter.translate(sx, sy)
        painter.rotate(self.ship_angle)
    
        SHIP_SCALE = 0.55  # slightly bigger
    
        # Solid outline
        painter.setPen(QColor(0, 0, 0))   # black outline
        painter.setBrush(QColor(255, 255, 255))  # bright white body
    
        ship = QPolygonF([
            QPointF(0, -20 * SHIP_SCALE),
            QPointF(12 * SHIP_SCALE, 16 * SHIP_SCALE),
            QPointF(0, 10 * SHIP_SCALE),
            QPointF(-12 * SHIP_SCALE, 16 * SHIP_SCALE)
        ])
    
        painter.drawPolygon(ship)
    
        # Optional: engine glow when thrusting
        if self.is_thrusting:
            painter.setBrush(QColor(255, 120, 40))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(-3.0, 16.0 * SHIP_SCALE, 6.0, 8.0))
    
        painter.restore()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_A:
            self.rotating_left = True
        elif event.key() == Qt.Key_D:
            self.rotating_right = True

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging_map = True
            self.last_mouse_pos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging_map = False
            self.last_mouse_pos = None
        super().mouseReleaseEvent(event) 

    def update_simulation(self, dt):
        # Manual control ONLY when auto-correction is OFF
        if not self.enable_auto_correction:
            if self.rotating_left:
                self.ship_angle -= self.rotation_speed * dt
            if self.rotating_right:
                self.ship_angle += self.rotation_speed * dt
    
            self.ship_angle %= 360
    
    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_A:
            self.rotating_left = False
        elif event.key() == Qt.Key_D:
            self.rotating_right = False

    def startOrbit(self):
        if self.sim_running:
            self.timer.stop()
            self.sim_running = False
            self.btn8.setText("Start simulation")
            # reset to initial angle and position
            self.resetStarshipPosition()
            self.path_points.clear()
            self.recompute_prediction()
            self.update()
            return
        
        # start timer using existing interval (we keep 16ms for rendering)
        self.timer.start()
        self.sim_running = True
        self.btn8.setText("Stop simulation")
        # Setup a target orbit instruction (use LEO as the target by default)
        try:
            target_alt = LEO_ALTITUDE_KM.get(self.selected_planet, None)
            if target_alt is not None:
                self.orbit_target_alt = float(target_alt)
                r_target = self.planet_real_radius_km + self.orbit_target_alt
                # circular velocity v = sqrt(mu / r)
                self.orbit_target_v = math.sqrt(PLANET_MU[self.selected_planet] / r_target)
                self.orbit_locked = False
                self.orbit_lock_counter = 0
                self.instructionLabel.setText(
                    f"Target orbit: {self.orbit_target_alt} km. Aim for speed ≈ {self.orbit_target_v:.3f} km/s.\nUse thrust controls to adjust altitude and velocity until lock is achieved."
                )
                self.instructionLabel.adjustSize()
                self.instructionLabel.move(10, 60)
                self.instructionLabel.setVisible(True)
        except Exception:
            pass
    
# ... rest of SpaceWindowUI class ...

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = SpaceWindowUI()
    window.show()
    sys.exit(app.exec())
    


