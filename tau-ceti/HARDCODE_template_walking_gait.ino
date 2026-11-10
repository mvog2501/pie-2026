#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

const uint32_t OSC_FREQ = 27488192;   // your calibrated value
const uint16_t US_MIN = 670;
const uint16_t US_MAX = 2470;

// Channels
const int b1 = 0;  const int b1j = 7;  const int b1f = 8;
const int b2 = 1;  const int b2j = 5;  const int b2f = 9;
const int b3 = 2;  const int b3j = 15; const int b3f = 11;
const int b4 = 3;  const int b4j = 13; const int b4f = 10;

// Walking settings (keep small while testing)
const float STRIDE_DEG = 8;          // hip swing either side of 90
const float LIFT_DEG = 8;            // joint lift; joint "-" is up
const unsigned long CYCLE_MS = 8000; // one full gait cycle, bigger = slower
const unsigned long RAMP_MS = 6000;  // boot ramp from 90 to standing pose

struct Leg {
  int hip, joint, foot;
  float standHip, standJoint, standFoot;
  float hipSign;    // flip to -1 if a leg walks backward
  float phase;      // 0 to 1, sets the order legs step in
};

// Hip standing values are placeholders at 90 until you measure them
Leg LEGS[4] = {
  {b1, b1j, b1f, 90, 127, 26, +1, 0.00},
  {b2, b2j, b2f, 90, 125, 30, +1, 0.50},
  {b3, b3j, b3f, 90, 111, 32, +1, 0.25},
  {b4, b4j, b4f, 90, 126, 32, +1, 0.75},
};

bool walking = false;

uint16_t angleToUs(float angle) {
  if (angle < 0) angle = 0;
  if (angle > 180) angle = 180;
  return US_MIN + (uint16_t)((angle / 180.0) * (US_MAX - US_MIN));
}

void writeAngle(int ch, float angle) {
  pwm.writeMicroseconds(ch, angleToUs(angle));
}

// Moves every servo from 90 to its standing pose together, so none jump
void rampToStand() {
  unsigned long start = millis();
  while (true) {
    float t = (millis() - start) / (float)RAMP_MS;
    if (t > 1) t = 1;
    for (int i = 0; i < 4; i++) {
      Leg &L = LEGS[i];
      writeAngle(L.hip,   90 + (L.standHip   - 90) * t);
      writeAngle(L.joint, 90 + (L.standJoint - 90) * t);
      writeAngle(L.foot,  90 + (L.standFoot  - 90) * t);
    }
    if (t >= 1) break;
    delay(20);
  }
}

void holdStand() {
  for (int i = 0; i < 4; i++) {
    Leg &L = LEGS[i];
    writeAngle(L.hip,   L.standHip);
    writeAngle(L.joint, L.standJoint);
    writeAngle(L.foot,  L.standFoot);
  }
}

void updateWalk() {
  float cycle = (millis() % CYCLE_MS) / (float)CYCLE_MS;

  for (int i = 0; i < 4; i++) {
    Leg &L = LEGS[i];
    float p = cycle + L.phase;
    if (p >= 1) p -= 1;

    float hipMove, lift;
    if (p < 0.25) {
      // Swing: lift and move forward
      hipMove = -cos(PI * p / 0.25);
      lift = LIFT_DEG * sin(PI * p / 0.25);
    } else {
      // Stance: foot on ground, body pushed forward
      hipMove = cos(PI * (p - 0.25) / 0.75);
      lift = 0;
    }

    writeAngle(L.hip,   L.standHip + L.hipSign * STRIDE_DEG * hipMove);
    writeAngle(L.joint, L.standJoint - lift);
    writeAngle(L.foot,  L.standFoot);
  }
}

void setup() {
  Serial.begin(9600);
  Wire.begin();

  pwm.begin();
  pwm.setOscillatorFrequency(OSC_FREQ);
  pwm.setPWMFreq(50);
  delay(10);

  rampToStand();
  Serial.println("Standing. Send w to walk, s to stop.");
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'w') {
      walking = true;
      Serial.println("Walking");
    } else if (c == 's') {
      walking = false;
      holdStand();
      Serial.println("Stopped, standing");
    }
  }

  if (walking) updateWalk();
  delay(20);
}