# State Classification

## Driving States

1. Idle
2. Traffic
3. Cruising
4. Acceleration
5. Deceleration

---

## Idle

Conditions:
- speed <= 2 km/h
- rpm > 600

---

## Traffic

Conditions:
- speed > 2 km/h
- speed <= 40 km/h

---

## Cruising

Conditions:
- speed > 40 km/h
- stable speed
- stable rpm

---

## Acceleration

Conditions:
- speed_delta > threshold
- throttle_delta > threshold

---

## Deceleration

Conditions:
- speed_delta < threshold
- throttle position low