## Input --------> Engine --------> output





# Spaceflight UI + Physics Notes



## 1️⃣ Physics Engine:



* State variables: (x, y) position, (vx, vy) velocity, (ax, ay) acceleration, mass, orientation.



* Update each timestep dt:

&nbsp;         Compute net force: F\_net = F\_thrust + F\_gravity + F\_disturbance

&nbsp;         Compute acceleration: a = F\_net / mass

&nbsp;         Update velocity: v += a \* dt

&nbsp;         Update position: x += v \* dt

&nbsp;         Fuel consumption: dynamically reduce fuel as thrust is applied

&nbsp;         Predict stopping point: estimate where spacecraft will stop on 2D plane based on current velocity, thrust, and remaining fuel

&nbsp;         Planet rotation effect: optionally include planet rotation influence on orbit





## 2️⃣ Input Layer:



* User controls: buttons for propulsion type, gravity toggle, destination position on the 2d plane.



* Planet selection: choose which planet to orbit or navigate around



* Speed option: ability to speed up simulation time for faster orbit/travel visualization



* Hovering shows read-only info (velocity, thrust, orbital parameters).



* Physics engine “listens” to inputs each timestep.





## 3️⃣ Dynamic Orbit \& Visualization:



* Draw planet as circle.



* Dot = spacecraft.



* Orbit line updates based on position + velocity.



* Trail/history shows past path.



* Optional: velocity vectors, thrust arrows.



* Dynamically update orbit to reflect planet rotation and spacecraft motion



* Display fuel remaining visually (optional bar or numeric display)



## 4️⃣ Hover Tooltip:



Shows:



* Spacecraft name



* Thrust magnitude \& direction



* Velocity, acceleration



* Remaining fuel dynamically



* Optional: orbital parameters (semi-major axis, eccentricity, etc.), predicted stopping point



Tooltip is read-only, does not affect physics.



## 5️⃣ Propulsion Types:



* Chemical: high thrust, short bursts



* Ion: low thrust, continuous



* Cold gas: tiny thrust, fast response



* Optional: nuclear, solar sail, etc.



* Different types scale thrust magnitude and acceleration.



## 6️⃣ Loop / Flow:



* Read user inputs.



* Compute forces and update acceleration.



* Update velocity \& position.



* Update orbit \& visualization.



* Update hover tooltip if needed.



* Reduce fuel based on thrust applied



* Repeat every timestep for smooth simulation.



## 7️⃣ Key Principles:



* Keep units consistent.



* Apply thrust as vector.



* Gravity toward planet center.



* Modular design for inputs, physics, visualization.



* Retro-style UI keeps focus on physics, low memory.



* Dynamic simulation: fuel, predicted stopping point, time-speed control, planet effects






