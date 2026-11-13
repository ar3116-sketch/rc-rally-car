// RC rally car: phone control over Bluetooth for the Arduino Nano 33 BLE.
// Use the Adafruit Bluefruit Connect app: connect to "RC Rally", open Controller, then Control Pad.
//   Up / Down     drive while held
//   Left / Right  steer while held
//   Button 1 / 2  slow / fast
// Needs the "Arduino Mbed OS Nano Boards" package and the ArduinoBLE and Servo libraries.
// Compiles for the Nano 33 BLE, but has NOT run on hardware yet. Test with the wheels off the ground first.

#include <ArduinoBLE.h>
#include <Servo.h>

// Pins. The Nano's pins are 3.3 V only: the servo signal goes through the level shifter.
const int PIN_SERVO = 3;   // to level shifter LV side; HV side goes to the servo signal wire
const int PIN_AIN1 = 5;    // to DRV8833 AIN1 and BIN1 (bridge them). Motor power goes to the driver's VIN pin, not VMM.
const int PIN_AIN2 = 6;    // to DRV8833 AIN2 and BIN2 (bridge them). Join AOUT1+BOUT1 and AOUT2+BOUT2: the two
                           // channels in parallel give 2.4 A, above the motor's 1.5 A stall. One channel is only 1.2 A.
const int PIN_VBAT = A0;   // battery divider: battery+ to 100k to A0, A0 to 47k to GND

// Set these on the bench.
const int STEER_CENTER = 90;   // servo angle for straight ahead
const int STEER_TRAVEL = 20;   // servo degrees each way. Start low, then raise toward 37, which is full lock in the
                               // v2 model (25 deg inner wheel). Never above 40: past that the horn pin leaves its slot range.
static_assert(STEER_TRAVEL <= 38, "STEER_TRAVEL above 38 drives the steering past full lock");
const bool STEER_REVERSED = false;
const bool MOTOR_REVERSED = false;

// The motor is rated 6 V and a full 2S battery is 8.4 V, so never go above about 70%.
const int SPEED_SLOW = 70;     // out of 255, about 1 m/s with the 10:1 motor
const int SPEED_FAST = 178;    // out of 255, about 70%

// Stop driving below this to protect the LiPo. Averaged, so a short dip under load does not trip it.
const float VBAT_CUTOFF = 6.4;
const float VBAT_DIVIDER = (100.0 + 47.0) / 47.0;

BLEService uartService("6E400001-B5A3-F393-E0A9-E50E24DCCA9E");  // Nordic UART service, which the app talks to
BLECharacteristic rxChar("6E400002-B5A3-F393-E0A9-E50E24DCCA9E", BLEWrite | BLEWriteWithoutResponse, 20);
BLECharacteristic txChar("6E400003-B5A3-F393-E0A9-E50E24DCCA9E", BLENotify, 20);

Servo steering;
bool btnUp = false, btnDown = false, btnLeft = false, btnRight = false;
int speedLimit = SPEED_SLOW;
bool batteryLow = false;
float vbatAverage = 8.0;
unsigned long lastBatteryCheck = 0;

void setMotor(int power) {  // -255 to 255
  if (MOTOR_REVERSED) power = -power;
  analogWrite(PIN_AIN1, power > 0 ? power : 0);
  analogWrite(PIN_AIN2, power < 0 ? -power : 0);
}

void applyControls() {
  int drive = 0;
  if (!batteryLow) {
    if (btnUp && !btnDown) drive = speedLimit;
    if (btnDown && !btnUp) drive = -speedLimit;
  }
  setMotor(drive);

  int steer = 0;
  if (btnLeft && !btnRight) steer = STEER_TRAVEL;
  if (btnRight && !btnLeft) steer = -STEER_TRAVEL;
  if (STEER_REVERSED) steer = -steer;
  steering.write(STEER_CENTER + steer);
}

void stopEverything() {
  btnUp = btnDown = btnLeft = btnRight = false;
  applyControls();
}

// App button packet: '!' 'B' button state checksum. The checksum is the inverted sum of the first four bytes.
void handlePacket(const uint8_t* data, int length) {
  if (length < 5 || data[0] != '!' || data[1] != 'B') return;
  uint8_t sum = 0;
  for (int i = 0; i < 4; i++) sum += data[i];
  if ((uint8_t)~sum != data[4]) return;

  bool pressed = data[3] == '1';
  switch (data[2]) {
    case '1': if (pressed) speedLimit = SPEED_SLOW; break;
    case '2': if (pressed) speedLimit = SPEED_FAST; break;
    case '5': btnUp = pressed; break;
    case '6': btnDown = pressed; break;
    case '7': btnLeft = pressed; break;
    case '8': btnRight = pressed; break;
  }
  applyControls();
}

void checkBattery() {
  if (millis() - lastBatteryCheck < 200) return;
  lastBatteryCheck = millis();
  float volts = analogRead(PIN_VBAT) * 3.3 / 1023.0 * VBAT_DIVIDER;
  if (volts < 3.0) {  // running from USB with the car switched off: there is no battery to protect
    vbatAverage = 8.0;
    return;
  }
  vbatAverage = vbatAverage * 0.95 + volts * 0.05;  // about a 4 second average
  if (vbatAverage < VBAT_CUTOFF && !batteryLow) {
    batteryLow = true;  // stays off until the power is cycled
    applyControls();
  }
  if (batteryLow) digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
}

void setup() {
  pinMode(PIN_AIN1, OUTPUT);
  pinMode(PIN_AIN2, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);
  setMotor(0);
  steering.attach(PIN_SERVO);
  steering.write(STEER_CENTER);

  float startVolts = analogRead(PIN_VBAT) * 3.3 / 1023.0 * VBAT_DIVIDER;
  if (startVolts >= 3.0) vbatAverage = startVolts;

  if (!BLE.begin()) {
    while (true) {  // fast blink: Bluetooth failed to start
      digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
      delay(100);
    }
  }
  BLE.setLocalName("RC Rally");
  BLE.setAdvertisedService(uartService);
  uartService.addCharacteristic(rxChar);
  uartService.addCharacteristic(txChar);
  BLE.addService(uartService);
  BLE.advertise();
}

void loop() {
  BLE.poll();
  checkBattery();

  BLEDevice central = BLE.central();
  static bool wasConnected = false;
  bool connected = central && central.connected();

  // If the phone disconnects or goes out of range, stop. The app only sends press and release,
  // so a held button sends nothing and a timer would stop the car while you are still driving.
  if (wasConnected && !connected) stopEverything();
  wasConnected = connected;

  if (connected && rxChar.written()) {
    handlePacket(rxChar.value(), rxChar.valueLength());
  }
}
