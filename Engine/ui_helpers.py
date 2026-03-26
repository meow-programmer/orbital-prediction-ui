from PyQt5.QtGui import QPainter, QColor, QBrush, QPalette

def updateButtonPositions(self):
    # Paste in your existing implementation (unchanged). Kept short for readability.
    window_width = self.width()
    box_width = 260
    box_height = 100
    box_x = window_width - box_width - 20
    box_y = self.height() - box_height - 20
    self.sliderBox.setGeometry(box_x, box_y, box_width, box_height)
    self.slider.resize(int(box_width * 0.80), 20)
    slider_x = (box_width - self.slider.width()) // 2
    slider_y = 40
    self.slider.move(slider_x, slider_y)
    self.sliderTitle.adjustSize()
    title_x = (box_width - self.sliderTitle.width()) // 2
    self.sliderTitle.move(title_x, 10)
    # ... your existing sliderBox/slider placement ...

    # place livePosLabel first
    pos_x = self.sliderBox.x() + 8
    pos_y = self.sliderBox.y() - self.livePosLabel.height() - 8
    self.livePosLabel.move(pos_x, pos_y)
    self.livePosLabel.raise_()

    # place liveSpeedLabel immediately to the right of livePosLabel
    speed_x = pos_x + self.livePosLabel.width() + 10  # 10px gap
    speed_y = pos_y
    # make sure it doesn't go offscreen
    speed_x = min(speed_x, self.width() - self.liveSpeedLabel.width() - 8)
    self.liveSpeedLabel.move(speed_x, speed_y)
    self.liveSpeedLabel.raise_()
    try:
        label_x = self.sliderBox.x() + 8 + self.livePosLabel.width() + 10  # offset a bit to right
        label_y = self.sliderBox.y() - self.liveSpeedLabel.height() - 8
        label_x = max(8, min(label_x, self.width() - self.liveSpeedLabel.width() - 8))
        label_y = max(8, label_y)
        self.liveSpeedLabel.move(label_x, label_y)
        self.liveSpeedLabel.raise_()
    except Exception:
        pass
    # position right-side buttons
    self.buttons = [
        self.btn1, self.btn2, self.btn3,
        self.btn4, self.btn5, self.btn6,
        self.btn7, self.btn8, self.toggle
    ]
    pad_x = 20
    pad_y = 20
    current_y = pad_y
    for btn in self.buttons:
        x = window_width - btn.width() - pad_x
        y = current_y
        btn.move(x, y)
        if btn == self.btn1:
            self.positionBox.move(x, y + btn.height())
            if self.positionBox.isVisible():
                current_y += self.positionBox.height()
        if btn == self.btn2:
            self.destBox.move(x, y + btn.height())
            if self.destBox.isVisible():
                current_y += self.destBox.height()
        if btn == self.btn3:
            self.propulsionOptions.move(x, y + btn.height())
            if self.propulsionOptions.isVisible():
                current_y += self.propulsionOptions.height()
        if btn == self.btn4:
            self.massBox.move(x, y + btn.height())
            if self.massBox.isVisible():
                current_y += self.massBox.height()
        if btn == self.btn5:
            self.fuelBox.move(x, y+btn.height())
            if self.fuelBox.isVisible():
                current_y += self.fuelBox.height()
        if btn == self.btn6:
            # place planetOptions under this button when visible
            self.planetOptions.move(x, y + btn.height())
            if self.planetOptions.isVisible():
                current_y += self.planetOptions.height()
        if btn == self.btn7:
            label_x = x - self.simspeedlabel.width() - 5
            label_y = y
            self.simspeedlabel.move(label_x, label_y)
        current_y += btn.height()

def position_slider_labels(window):
    try:
        pos_x = window.sliderBox.x() + 8
        pos_y = window.sliderBox.y() - window.livePosLabel.height() - 8
        window.livePosLabel.move(pos_x, pos_y)
        speed_x = pos_x + window.livePosLabel.width() + 10
        speed_y = pos_y
        speed_x = min(speed_x, window.width() - window.liveSpeedLabel.width() - 8)
        window.liveSpeedLabel.move(speed_x, speed_y)
    except Exception:
        pass
    
def setPlanet(self, name):
    name_lower = name.lower()
    self.selected_planet = name.title()  # store for mass lookup
    
    if name_lower == 'earth':
        self.planet_real_radius_km = 6371
        self.planet_color = QColor(90, 150, 255)
    elif name_lower == 'mars':
        self.planet_real_radius_km = 3390
        self.planet_color = QColor(210, 120, 80)
    elif name_lower in ('moon', 'luna'):
        self.planet_real_radius_km = 1737
        self.planet_color = QColor(190, 190, 190)
    else:
        return
    
    self.planet_radius = max(2, int(round(self.planet_real_radius_km * self.km_to_px)))
    self.orbit_radius = 120 + (self.planet_radius // 5)
    
    self.btn6.setText(f"Planet: {name.title()}")
    self.planetOptions.setVisible(False)
    
    # reset orbit position for new planet (pick a reasonable altitude)
    self.resetStarshipPosition()
    self.update()

def world_to_screen(ui, x, y):
    """Convert world coordinates (km) → screen coordinates (pixels) with zoom."""
    scale = ui.zoom * ui.zoom_factor  # apply zoom factor here

    sx = ui.cx + x * scale
    sy = ui.cy - y * scale  # flip y-axis for screen
    return int(sx), int(sy)


  