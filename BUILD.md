# RC rally car: parts and build notes (v2, 13 Nov 2026)

Group B style body, 151.5 x 97 x 65.8 mm, 100.7 mm wide at full steering lock. Limit: 152.4 x 101.6 x 101.6 mm.
Source of truth: `rc_car.py` (run it in FreeCAD; it rebuilds `RC_Car.FCStd`, `RC_Car_assembly.step`, every STL and `rc_car_results.json`).
Checked in the model only. Nothing has been printed, wired or driven yet.

Body traced from the 1984 Audi Sport Quattro S1 blueprint by GetOutlines, CC BY 4.0:
https://getoutlines.com/blueprints/280/1984-audi-sport-quattro-s1-coupe-blueprints

## What v2 fixed (v1 would not have worked as drawn)

| v1 problem | v2 fix |
|---|---|
| Steering bound at about 15 deg of wheel lock: the horn pin drops 1.4 mm through its arc, the slot allowed 0.5 mm | Linkage solved properly (real Ackermann, inner 25 deg / outer 21.6 deg). Taller slot; the pin stays inside it at every angle (checked at 1/3, 2/3 and full lock both ways) |
| Tie rod pivot holes cut through its 2 mm bar (0.1 mm left) | New tie rod: 3 mm bar, 5.5 mm bosses, bridge over the pin, slotted tab |
| Kingpins, front wheels and tie-rod joints clamped solid when tightened; front wheels spun on screw threads | Knuckles turn on 4 mm round spacers, front wheels on 5 mm round spacers; screws clamp the spacers, not the moving parts. Tie-rod joints use nylon lock nuts |
| Rear bearings could not go in: the side wall crossed their path by 0.5 mm | Entry cut through the wall, plus a relief so only the outer ring seats |
| Gears were placeholder cylinders; the Nov 10 printed-gear macro put its gears inside the motor body | Real involute teeth, checked for clearance. Default: bought 0.5-module brass 12T/24T (2:1). Backup printed pair included |
| Power switch wiring was backwards: the #2810's control pin turns it ON when pulled high | Floor switch now goes between battery + and the ON pin |
| Motor driver single channel is 1.2 A, motor stalls at 1.5 A | Both DRV8833 channels in parallel (2.4 A) |
| Arduino Nano 33 BLE (ABX00030) is end of life | Use the Nano 33 BLE Rev2 (ABX00071), same size, holes and pins |
| 3 mm D-shaft and the 3 mm-wide collars in v1 are not sold | Round 3 mm shaft with filed flats; 4 mm round spacers replace the collars |

How the front end works now: each kingpin is 5 mm ahead of the axle (trail), which leaves room for the axle insert
beside the kingpin and makes the steering self-centre. The arms point back along the Ackermann line to the rear axle.

## Print list (`stl/`)

Print `FitTest_print_this_first.stl` first, in the same filament, and try every bought part in it: M2 and M3 insert
holes, magnet pocket, bearing pocket, M2 clearance, M1.6 pilot, locating pin, motor slot, the 4.2 mm knuckle bore
(4 mm spacer), the 5.2 mm wheel bore (5 mm spacer) and the 3 mm D bore (rear axle).

| Filament | Files |
|---|---|
| Body colour | Shell, Nose, Tail, Cabin, Wing, RimFL, RimFR, RimRL, RimRR |
| Dark | Tub, Glass, Splitter, Grille, VentHoodL/R, VentSideL/R, ElectronicsTray, MotorStrap |
| PETG (tough, for the steering) | KnuckleL, KnuckleR, TieRod |
| TPU 95A | TireFL, TireFR, TireRL, TireRR |
| Only if you print the backup gears | ALT_Pinion_12T_m0.6_printed, ALT_AxleGear_17T_m0.6_printed (0.25 mm nozzle or resin) |

Tyre bores are 0.3 mm under the rims: stretch them on, then wick in a drop of CA.

## Bought parts

| Qty | Part | Buy | Price (USD) |
|---|---|---|---|
| 1 | Arduino Nano 33 BLE **Rev2** (ABX00071) | store.arduino.cc | about 27 to 30, not confirmed |
| 1 | Micro metal gearmotor 10:1 HPCB 6 V | Pololu #3061 | 26.45 |
| 1 | DRV8833 dual motor driver carrier | Pololu #2130 | 10.95 |
| 1 | 5 V 2.5 A step-down regulator D24V22F5 | Pololu #2858 | 26.95 |
| 1 | 4-channel logic level shifter | Pololu #2595 | 3.49 |
| 1 | Mini MOSFET slide switch, LV | Pololu #2810 | 4.49 |
| 1 | SG90 9 g servo, with its single-arm horn | any (e.g. ReadyMadeRC 87004) | 2 to 9 |
| 1 | LiPo 2S 300 mAh 45C, JST-SYP, 40 x 20 x 12 mm | Gens Ace GEA3002S45JST | 8.99 |
| 1 | Mating JST-SYP plug with leads | any | about 2 |
| 1 | SS-12F15 slide switch (floor switch, signal only) | any | under 1 |
| 1 | Pinion 12T, 0.5 module, 3 mm D bore, 4 mm face, OD 7 | brass "0.5M 12T" N20 gear | about 2 to 5, not confirmed |
| 1 | Gear 24T, 0.5 module, 3 mm bore, set screw hub, OD 13, face 4, hub 8 OD x 4 or less | brass "0.5M 24T 3 mm" | about 2 to 5, not confirmed |
| 1 | Round shaft 3 mm x 100 mm, cut to 94 | ONDRIVES GPM3000-100 (Zoro) or Tamiya 70105 (Pololu #78) | 12.69 / set |
| 2 | 683ZZ bearing 3 x 7 x 3 | VXB kit767 (10-pack) | 29.99 / 10 |
| 2 | Brass round spacer 4 OD x 2.2 ID x 10 (kingpins) | Essentra 311221040050 | about 1 |
| 2 | Aluminium round spacer 5 OD x 3.2 ID x 9 (front axles) | Harwin R30-6200914 | about 1 |
| 2 | Aluminium round spacer 5 OD x 3.2 ID x 4 (rear axle) | Harwin R30-6200414 | about 1 |
| 24 | Magnets 6 x 2 mm N52 (12 pairs) | totalElement 150-pack | 22.79 / 150 |
| 11 | Heat insert M2 x 3 (hole 3.2, 4 deep) | CNC Kitchen / 3DJake | 11.07 / 100 |
| 2 | Heat insert M3 x 3 short (hole 4.0) | CNC Kitchen / 3DJake | 9.68 / 100 |
| 1 | Resistor 100 k, resistor 47 k (battery divider) | any | |
| 1 | Capacitor 0.1 uF ceramic (across motor), 220 uF 10 V (5 V rail) | any | |
| | Silicone wire 26 AWG (power) and 30 AWG (signal), heat shrink, foam tape, CA glue | any | |

Charger: SkyRC iMAX B6 V2 or any balance charger with adjustable current. Charge at 0.3 A (1C), never unattended.

## Fasteners (counted from the model)

| Qty | Part | Where |
|---|---|---|
| 5 | M2 x 4 socket head | Motor strap (1), electronics tray (2), regulator (2) |
| 4 | M2 x 5 socket head | Servo flange (2), cabin (2) |
| 2 | M2 x 16 socket head + M2 washer (5 OD) | Kingpins, through the 4 mm spacer into the ear insert |
| 2 | M3 x 12 socket head + M3 washer (7 OD) | Front axles, through the 5 mm spacer into the knuckle insert |
| 2 | M2 x 8 socket head + M2 nylon lock nut (4 AF x 2.8) | Tie rod to steering arms |
| 1 | M2 x 10 socket head | Horn pin, from the front, through the tie-rod slot, self-tapped into the horn |
| 4 | M1.6 x 4 socket head | Nano to tray, self-tapping |
| 1 | M2 set screw | Comes with the 24T gear |

## Assembly notes for the moving parts

**Rear axle.** Cut the shaft to 94 mm and deburr it. File a flat 0.5 mm deep (2.5 mm across) along 14 mm at each end and
where the gear's set screw lands. Press the 683ZZ bearings into the tub from outside. Slide the shaft in through one
bearing, thread on the 24T gear (hub facing +Y, away from the motor), then out through the other bearing. Add a 4 mm
spacer on each side, then press the rear wheels on until they hold the spacers against the bearing inner rings, with
the axle still turning freely. Wick CA into each wheel. Centre the gear on the pinion and tighten its set screw on the flat.

**Motor.** Press the 12T pinion onto the D shaft with its back face 1 mm off the gearbox face, so it lines up with the 24T. Drop the motor into the
cradle (the pinion meshes as it goes down), then fit the strap.

**Kingpins.** Melt an M2 insert into each steering ear (from the top). Sit the knuckle on the ear, push the 4 mm brass
spacer down through it, add the washer and the M2 x 16, and tighten hard. The knuckle must swing freely: the spacer is
0.5 mm longer than the knuckle.

**Front wheels.** Melt the M3 insert into the knuckle face. Push the 5 mm spacer through the wheel, then M3 washer and
M3 x 12 from the outside. Tighten hard: the wheel spins on the spacer with 0.2 mm end play.

**Steering.** Find the hole on the servo's single-arm horn nearest 6.1 mm from its centre (anything from 6 to 8.5 mm works)
and drill it 1.6 mm. Centre the servo (upload the sketch, it parks at 90 deg), then press the horn on pointing straight up.
Bolt the tie rod to both arms with M2 x 8 and nylon lock nuts: snug, then back off until the joint swings free. Thread
the M2 x 10 from the front through the tie-rod slot into the horn hole until its head sits 1.3 mm clear of the tab.

## Wiring

- Nano pins are 3.3 V only and not 5 V tolerant. Its 5 V pin does not supply power.
- Battery + to #2810 VIN, battery - to GND. Leave the #2810's own slide switch OFF.
- **Floor switch between #2810 VIN and its ON pin.** ON above about 1 V turns the car on; floating or low is off.
- #2810 VOUT feeds the Nano VIN, the DRV8833 VIN and the regulator VIN. Do not use the driver's VMM pin (protected output).
- DRV8833: bridge AIN1 to BIN1 and AIN2 to BIN2; join AOUT1 to BOUT1 and AOUT2 to BOUT2; the motor goes across the joined outputs.
- Regulator 5 V powers the servo and the level shifter's HV side. Nano 3.3 V powers the LV side. Share all grounds.
- Firmware limits the motor to 70% (178/255): a full battery is 8.4 V, the motor is rated 6 V.

| Nano pin | Goes to |
|---|---|
| D3 | Level shifter LV1; HV1 to the servo signal (orange) |
| D5 | DRV8833 AIN1 + BIN1 |
| D6 | DRV8833 AIN2 + BIN2 |
| A0 | Battery divider: battery + to 100 k to A0, A0 to 47 k to GND |
| VIN | #2810 VOUT |
| 3.3V | Level shifter LV |
| GND | Everything |

Wire run lengths from the model (add 30 mm each for slack and strip): motor to driver 94 mm, battery to switch board
61 mm, switch board to Nano 44 mm, driver to Nano 29 mm, regulator to servo 21 mm. Shorten the servo's own lead to fit.

## Driving it

Phone over Bluetooth with the Adafruit Bluefruit Connect app and `firmware/rc_car_drive/rc_car_drive.ino`
(Arduino Mbed OS Nano Boards, ArduinoBLE, Servo). It compiles but has not run on hardware. Connect to "RC Rally",
then Controller, then Control Pad. Up/Down drive, Left/Right steer, buttons 1/2 slow/fast. Disconnect stops the car;
below 6.4 V the motor cuts out and the LED blinks.

First run with the wheels off the ground. Start with `STEER_TRAVEL` 20 and raise it toward 37 (full lock in the model;
the sketch refuses anything above 38). Set `STEER_CENTER` so the car tracks straight.

## Measured in the model (`rc_car_results.json`)

| Measure | Result |
|---|---|
| Weight, printed parts counted solid | about 233 g, partly estimated |
| Centre of gravity height | 22.5 mm |
| Steering | inner 25 deg, outer 21.6 deg, servo 37.8 deg each way |
| Width at full lock | 100.7 mm (limit 101.6) |
| Tightest wheel gap at lock | 1.01 mm |
| Top speed, no load, 6 V | 2.76 m/s (motor speed is +/-20%); slow mode about 1 m/s |
| Drive margin | 4.5 x rolling drag on a flat floor at a quarter of stall force. Indoor flat floors, not hills |
| Tipping at full lock | from about 1.8 m/s if the tyres grip; allowed by choice |
| Ground clearance | 5.5 mm splitter, 6 mm tub |

## Measure before you print

- **SG90 flange holes and horn.** Makers differ and no maker publishes hole spacing. The model uses 28 mm between the
  servo screws and a 6.1 mm horn hole. Measure yours; `SERVO_SCREWS` and `HORN_R` in `rc_car.py` change them.
- **Brass gears.** Listings vary. The 24T must have OD 13 or less, face 4 mm, hub 8 mm OD or less and 4 mm or less long.
- **Shaft flats.** Flat depth only matters where the wheels and gear grip it.
- Wall thickness, print orientation and supports have not been checked in a slicer.

## Backup drive (printed gears)

If you would rather print the gears: 0.6 module, 12T (x = +0.32) on the motor, 17T (x = +0.24) on the axle, same
9.0 mm centres, contact ratio 1.28. Ratio 1.42:1, so top speed rises to about 3.9 m/s and drive margin drops to about
3.2. Needs a 0.25 mm nozzle or resin; PETG or nylon, not PLA.

## Cost for one car (USD, before shipping and tax)

About $200 to $230 for the bought parts above, plus about $25 to $40 of screws, wire, glue and filament. Brass gear
and spacer prices are estimates. Spare inserts, magnets and bearings carry over to a second car.
