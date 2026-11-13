# RC car, Group B rally body traced from a side and top blueprint (see TRACE below). Source of truth: change numbers here and re-run, never edit the output.
# Run inside FreeCAD: exec(open(path).read(), {"OUT_DIR": folder})
# Axes: X forward, Y left, Z up, ground at Z=0. Units: mm.
import json, math, os
import FreeCAD as App
import Part, Sketcher
from FreeCAD import Vector as V

try:
    import FreeCADGui as Gui
except ImportError:
    Gui = None

# Output folder: OUT_DIR if the caller set one, else the folder this script is in (FreeCAD: Macro > Macros... > Execute).
OUT_DIR = globals().get("OUT_DIR") or (os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd())

# ---------- Requirements (limit, source) ----------
ENVELOPE = (152.4, 101.6, 101.6)  # user: finished car 6 x 4 x 4 in maximum, including at steering lock
PRINTER = (256.0, 256.0, 256.0)   # user: printer build volume
STEER_DEG = 25.0                  # assumed steering lock, no clash required

# ---------- Parameters ----------
WHEEL_R = 16.0
FRONT_IN, FRONT_OUT = 33.0, 44.0   # v2: 1 mm narrower so the outer wheel stays inside 4 in at full lock
REAR_IN, REAR_OUT = 33.0, 47.0
AXLE_Z = WHEEL_R
X_FRONT, X_REAR = 44.0, -48.0
KINGPIN_Y = 28.0
# v2: the kingpin sits KP_TRAIL ahead of the axle. That leaves room for the M3 axle insert beside the kingpin bore,
# and the trail makes the steering self-centre. Kingpin and front axle both turn on bought round spacers, so no
# pivot clamps when its screw is tightened and nothing turns on screw threads.
KP_TRAIL = 5.0
KP_X = 44.0 + KP_TRAIL
KP_SPACER = (4.0, 2.2, 10.0)       # brass round spacer 4 OD x 2.2 ID x 10 (Essentra 311221040050): 10 mm is the longest sold
AX_SPACER = (5.0, 3.2, 9.0)        # aluminium round spacer 5 OD x 3.2 ID x 9 (Harwin R30-6200914)
REAR_SPACER = (5.0, 3.2, 4.0)      # same family, 4 mm (Harwin R30-6200414): bearing inner ring to rear wheel hub
EAR_TOP = 12.0
ARM_LEN = 10.5                     # kingpin to tie-rod pivot, along the Ackermann line to the rear axle centre
HORN_R = 6.1                       # SG90 horn hole radius used for the pin (6 to 8.5 works): drill it 1.6 mm, the M2 pin self-taps
Z_BOTTOM, FLOOR_T = 6.0, 2.5
Z_RAIL = 13.0
KICK_X, TAIL_X, KICK_Z = -50.0, -62.0, 10.5
NOSE_X, SHELF_X = 58.0, 66.0
BODY_Z0 = 7.0
WALL = 1.6
MAG_R, MAG_T, MAG_CLEAR = 3.0, 2.0, 0.1
BEARING_R, BEARING_T = 3.5, 3.0  # 683ZZ: 3 x 7 x 3
BEARING_RELIEF_R = 2.6           # clears the 683 inner ring face

# Heat-set inserts, CNC Kitchen spec: (outer d, tip d, length, hole d, minimum wall).
INSERT_M2 = (3.6, 3.1, 3.0, 3.2, 1.3)   # M2 x 3.0
INSERT_M3 = (4.6, 3.9, 3.0, 4.0, 1.6)   # M3 short x 3.0
INSERT_HOLE_DEPTH = 4.0                 # CNC Kitchen: blind holes at least insert length + 1 mm
# ISO 4762 socket head cap screws: nominal -> (head d, head height, hex across flats).
SCREW_DIMS = {1.6: (3.0, 1.6, 1.5), 2: (3.8, 2.0, 1.5), 3: (5.5, 3.0, 2.5)}
CLEAR_M2 = 1.1  # clearance hole radius for M2

# Fastener positions.
STRAP_SCREW = (-30.0, -5)
TRAY_SCREWS = [(-30.5, 11), (-3.7, -11)]
REG_CENTER = (44.9, -10.1)                # Pololu D24V22F5: 17.8 square, holes 13.21 apart at opposite corners
REG_SCREWS = [(REG_CENTER[0] - 6.605, REG_CENTER[1] - 6.605), (REG_CENTER[0] + 6.605, REG_CENTER[1] + 6.605)]
SERVO_Y = -5.5
SERVO_HOLE_Z = 14.4
SERVO_SCREWS = [SERVO_Y - 14.0, SERVO_Y + 14.0]  # 28 mm spacing inside the open flange slots: measure your servo
CANOPY_SCREW = (0.0, 16.5)
NANO_X0 = -29.0                           # Arduino Nano 33 BLE: 43.16 x 17.76, 4 x d1.65 holes on 40.64 x 15.24
NANO_HOLES = [(NANO_X0 + 1.26 + dx, s * 7.62) for dx in (0, 40.64) for s in (1, -1)]

# Reference for the trace: 1984 Audi Sport Quattro S1 blueprint, getoutlines.com/blueprints/280, CC BY 4.0.
# Blueprint pixels map onto this car by anchoring the wheel centres: front wheel px 247 -> x 44, rear wheel px 763 -> x -48.
# Overhangs are compressed to fit the length limit, heights use 0.2 mm per px above the ground line at py 342,
# and plan widths use 0.2425 mm per px from the centreline at py 570. Wheels and track stay as the tub needs them.
FACE_X = 70.0   # front face of the body. The splitter wedge carries on to the length limit.
def trace_x(px):
    if px < 247:
        return 44 + (247 - px) * 0.137
    if px > 763:
        return -48 - (px - 763) * 0.141
    return 44 + (247 - px) * 92.0 / 516.0


def trace_z(py):
    return (342 - py) * 0.2


# Traced centreline points (px, py): hood, windshield base, roof, hatch, tail.
TRACE = [(75, 172), (120, 152), (200, 143), (350, 135), (480, 45), (600, 38), (690, 37), (770, 58), (900, 105), (945, 123)]

# Sections must not land on a seam plane (x=58, x=-62): coincident planes corrupt the cut.
# Body master form, flat panels: x, half width, flare top z, fender crest y, fender crest z, centreline z.
BODY = [(-75, 46, 31, 40, 41, 44), (-70, 47.5, 31.5, 40, 42, 45.6), (-60.5, 48.5, 32, 40, 42.5, 50), (-48, 48.5, 32, 40, 42, 41.5),
        (-38, 48.5, 31, 40, 41.5, 41), (-29, 47, 29, 39, 41, 41), (-24, 44.5, 25, 38, 41, 41), (5, 44.5, 25, 38, 41, 41),
        (16, 45, 25.5, 38, 41, 41), (21, 48.5, 27, 39.5, 41.5, 41), (44, 48.5, 27.5, 39.5, 41.5, 40.3), (57.5, 48, 27, 39, 40, 38.6),
        (66, 46, 25, 37, 36.5, 35), (FACE_X, 44, 23, 35, 34.5, 34)]
# Cabin: x, half width at the belt, half width at the roof, roof z. The ends stay buried under the body.
CANOPY = [(30, 36, 22, 37), (2.2, 36, 28, 59.4), (-35, 36, 28.5, 61), (-49, 35, 27, 56.8), (-61.5, 33, 24, 49)]
CANOPY_BASE = 23.0
CABIN_BELT = 43.0
ROOF_OPENING = [(22, -14), (22, 14), (16, 22.5), (-48, 22.5), (-54, 16), (-54, -16), (-48, -22.5), (16, -22.5)]  # stays under the cabin, which meets the hood near x=25

TUB_OUTER = [(-62, 31), (18, 31), (26, 22), (58, 22), (58, -22), (26, -22), (18, -31), (-62, -31)]
TUB_INNER = [(-60, 29), (17.2, 29), (25.2, 20), (54, 20), (54, -20), (25.2, -20), (17.2, -29), (-60, -29)]


# ---------- Steering linkage (v2): solved, not assumed ----------
# Arms point back along the line from each kingpin to the rear axle centre (Ackermann). One rigid tie rod joins the
# arm tips; the servo horn pushes its centre sideways through a pin in a vertical slot.
_ACK = math.atan2(KINGPIN_Y, KP_X - X_REAR)
ARM_TIP = (KP_X - ARM_LEN * math.cos(_ACK), KINGPIN_Y - ARM_LEN * math.sin(_ACK))
HORN_AXIS = (0.0, 14.4)          # servo output shaft (y, z), points +X
PIN_Z0 = HORN_AXIS[1] + HORN_R   # horn pin height at straight ahead
SLOT_Z = (17.7, 24.1)            # vertical slot in the tie-rod tab, pin is 2.0 mm
SLOT_HALF_W = 1.25               # 2.5 mm wide: the rod yaws a few degrees at lock
SLOT_X = 34.65                   # middle of the slot tab along X


def _rot2(p, c, deg):
    a = math.radians(deg)
    dx, dy = p[0] - c[0], p[1] - c[1]
    return (c[0] + dx * math.cos(a) - dy * math.sin(a), c[1] + dx * math.sin(a) + dy * math.cos(a))


def linkage(left_deg):
    """Left knuckle turned left_deg (CCW from above, + = turning left). Returns the right knuckle angle that keeps the
    tie rod its length, and the rod pose: (right_deg, tip_left, tip_right, centre, yaw_deg)."""
    tl = _rot2(ARM_TIP, (KP_X, KINGPIN_Y), left_deg)
    target = 2 * ARM_TIP[1]
    lo, hi = -60.0, 60.0
    def err(d):
        tr = _rot2((ARM_TIP[0], -ARM_TIP[1]), (KP_X, -KINGPIN_Y), d)
        return math.hypot(tl[0] - tr[0], tl[1] - tr[1]) - target
    for _ in range(80):
        mid = (lo + hi) / 2
        if (err(lo) > 0) == (err(mid) > 0):
            lo = mid
        else:
            hi = mid
    tr = _rot2((ARM_TIP[0], -ARM_TIP[1]), (KP_X, -KINGPIN_Y), mid)
    centre = ((tl[0] + tr[0]) / 2, (tl[1] + tr[1]) / 2)
    yaw = math.degrees(math.atan2(-(tl[0] - tr[0]), tl[1] - tr[1]))
    return mid, tl, tr, centre, yaw


def steer_pose(inner_deg, turn):
    """turn=+1 left, -1 right. Returns (left_deg, right_deg, rod centre dy, rod centre dx, rod yaw, horn_deg)."""
    if turn > 0:
        l, r = inner_deg, linkage(inner_deg)[0]
    else:  # mirror image of a left turn
        r_m = linkage(inner_deg)[0]
        l, r = -r_m, -inner_deg
    # Solve the rod pose from the left angle in either case.
    r2, tl, tr, c, yaw = linkage(l)
    dy = c[1]
    # The horn has to put its pin on the slot centre, which sits ahead of the tab, not at the rod centre.
    slot_y = dy + (SLOT_X - ARM_TIP[0]) * math.sin(math.radians(yaw))
    horn = math.degrees(math.asin(max(-1.0, min(1.0, slot_y / HORN_R))))
    return l, r2, dy, c[0] - ARM_TIP[0], yaw, horn


OUTER_DEG = abs(steer_pose(STEER_DEG, 1)[1])   # outer wheel angle at full inner lock


def floor_bottom(x):
    return Z_BOTTOM if x >= KICK_X else Z_BOTTOM + (KICK_X - x) / (KICK_X - TAIL_X) * (KICK_Z - Z_BOTTOM)


def floor_top(x):
    return floor_bottom(x) + FLOOR_T


# ---------- Document ----------
if "RC_Car" in App.listDocuments():
    App.closeDocument("RC_Car")
doc = App.newDocument("RC_Car")


# ---------- Part Design helpers ----------
def new_sketch(body, name, plane, offset=0.0):
    sk = body.newObject("Sketcher::SketchObject", name)
    feats = body.Origin.OriginFeatures
    support = {"XY": feats[3], "XZ": feats[4], "YZ": feats[5]}[plane]
    attr = "AttachmentSupport" if hasattr(sk, "AttachmentSupport") else "Support"
    setattr(sk, attr, [(support, "")])
    sk.MapMode = "FlatFace"
    sk.AttachmentOffset = App.Placement(V(0, 0, offset), App.Rotation())
    return sk


def add_poly(sk, pts):
    n = sk.GeometryCount
    k = len(pts)
    for i in range(k):
        a, b = pts[i], pts[(i + 1) % k]
        sk.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)), False)
    for i in range(k):
        sk.addConstraint(Sketcher.Constraint("Coincident", n + i, 2, n + (i + 1) % k, 1))


def add_rect(sk, x0, x1, y0, y1):
    add_poly(sk, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def add_circle(sk, x, y, r):
    sk.addGeometry(Part.Circle(V(x, y, 0), V(0, 0, 1), r), False)


def finish(feature, sk):
    doc.recompute()
    if feature.State and "Invalid" in feature.State:
        raise RuntimeError("%s failed: %s" % (feature.Name, feature.getStatusString()))
    if sk.ViewObject:
        sk.ViewObject.Visibility = False
    return feature


def pad(body, name, plane, offset, height, draw, midplane=False, reverse=False):
    sk = new_sketch(body, "Sk_" + name, plane, offset)
    draw(sk)
    f = body.newObject("PartDesign::Pad", name)
    f.Profile = sk
    f.Length = height
    f.Midplane = midplane
    f.Reversed = reverse
    f.Refine = True
    return finish(f, sk)


def pocket(body, name, plane, offset, depth, draw, reverse=False):
    """Blind pocket when depth is given, symmetric through-all when depth is None."""
    before = body.Shape.Volume
    sk = new_sketch(body, "Sk_" + name, plane, offset)
    draw(sk)
    f = body.newObject("PartDesign::Pocket", name)
    f.Profile = sk
    f.Refine = True
    if depth is None:
        f.Type = "ThroughAll"
        f.Midplane = True
    else:
        f.Length = depth
        f.Reversed = reverse
    finish(f, sk)
    if before - body.Shape.Volume < 1e-3:
        raise RuntimeError("Pocket %s removed no material" % name)
    return f


def rect_pair(sk, x0, x1, y0, y1):
    add_rect(sk, x0, x1, y0, y1)
    add_rect(sk, x0, x1, -y1, -y0)


# ---------- MERGE: the tub is one continuous body grown from the floor ----------
tub = doc.addObject("PartDesign::Body", "Tub")


def draw_floor(sk):
    add_poly(sk, [(TAIL_X, KICK_Z), (KICK_X, Z_BOTTOM), (SHELF_X, Z_BOTTOM), (SHELF_X, Z_BOTTOM + FLOOR_T),
                  (KICK_X, Z_BOTTOM + FLOOR_T), (TAIL_X, KICK_Z + FLOOR_T)])


pad(tub, "Floor", "XZ", 0, 62, draw_floor, midplane=True)


def draw_trim(sk):
    for s in (1, -1):
        add_poly(sk, [(18, 31 * s), (26, 22 * s), (NOSE_X, 22 * s), (NOSE_X, 18 * s), (70, 18 * s),
                      (70, 40 * s), (18, 40 * s)])


pocket(tub, "PlanOutline", "XY", 0, None, draw_trim)


def draw_rails(sk):
    add_poly(sk, TUB_OUTER)
    add_poly(sk, TUB_INNER)


pad(tub, "SideWalls", "XY", Z_BOTTOM, Z_RAIL - Z_BOTTOM, draw_rails)
pad(tub, "FrontWall", "XY", 7, 15.5 - 7, lambda sk: add_rect(sk, 54, NOSE_X, -20, 20))
pad(tub, "TailWall", "XY", 7, 24 - 7, lambda sk: add_rect(sk, TAIL_X, -59, -20, 20))
pad(tub, "AxleUprights", "XY", 7, 23 - 7, lambda sk: rect_pair(sk, -53, -43, 24, 29))
pad(tub, "SteeringEars", "XY", Z_BOTTOM, EAR_TOP - Z_BOTTOM, lambda sk: rect_pair(sk, KP_X - 3, KP_X + 3, 20, 31))

# Motor: drops straight in. The strap's tongue hooks a slot in the rear wall, and one screw clamps the front.
# The axle leaves no room for a rear screw, and a fixed lip would block the motor going in.
pad(tub, "MotorCradle", "XY", 7, 11 - 7, lambda sk: add_rect(sk, -46.1, -33, -15, 3))
pad(tub, "MotorRearWall", "XY", 7, 24 - 7, lambda sk: add_rect(sk, -46.1, -45.1, -15, 3))
pad(tub, "MotorFrontWall", "XY", 7, 14 - 7, lambda sk: add_rect(sk, -32.9, -31.6, -15, 3))
pad(tub, "MotorEndStop", "XY", 7, 13 - 7, lambda sk: add_rect(sk, -45, -33, -19.2, -18.1))
pad(tub, "StrapPost", "XY", 7, 21 - 7, lambda sk: add_rect(sk, -32.9, -27.1, -8, -2))
# v2: the MOSFET switch board stands on the inside of the front wall, out of the steering arm's swing.
pad(tub, "PowerBoardWall", "XY", 7, 31.2 - 7, lambda sk: add_rect(sk, 54, 55.5, -9, 9))

# Battery bay: Gens Ace 2S 300 mAh 45C, 40 x 20 x 12 mm. The tray above stops it lifting out while driving.
def draw_stops(sk):
    add_rect(sk, -28.2, -27, -26.9, 26.9)
    add_rect(sk, -6.6, -4.6, -21.5, 21.5)


pad(tub, "BatteryEndStops", "XY", 7, 14 - 7, draw_stops)
pad(tub, "BatterySideStops", "XY", 7, 12 - 7, lambda sk: rect_pair(sk, -27, -6.6, 20.3, 21.5))
TRAY_Z = 24.8
pad(tub, "TrayRearPost", "XY", 7, TRAY_Z - 7, lambda sk: add_rect(sk, -33.4, -27.6, 8, 14))
pad(tub, "TrayFrontPost", "XY", 7, TRAY_Z - 7, lambda sk: add_rect(sk, -6.6, -0.8, -14, -8))


def draw_servo_towers(sk):
    add_rect(sk, 9.5, 16, SERVO_SCREWS[0] - 2.9, SERVO_SCREWS[0] + 2.9)
    add_rect(sk, 9.5, 16, SERVO_SCREWS[1] - 2.9, SERVO_SCREWS[1] + 2.9)


pad(tub, "ServoTowers", "XY", 7, 20.3 - 7, draw_servo_towers)


def draw_shell_pads(sk):
    rect_pair(sk, -3, 13, 22, 29.2)
    rect_pair(sk, -42.5, -33.5, 23, 29.2)


pad(tub, "ShellPads", "XY", 7, Z_RAIL - 7, draw_shell_pads)
pad(tub, "RegulatorBosses", "XY", 7, 11.5 - 7, lambda sk: [add_circle(sk, x, y, 3.0) for x, y in REG_SCREWS])
pad(tub, "SwitchPocketWall", "XY", 7, 12 - 7, lambda sk: add_rect(sk, 34, 53.7, 13.4, 14))


def draw_shell_pins(sk):
    add_circle(sk, 0, 25.5, 2.0)
    add_circle(sk, 0, -25.5, 2.0)


pad(tub, "ShellPins", "XY", Z_RAIL - 0.5, 2.5, draw_shell_pins)


def draw_tail_pins(sk):
    add_circle(sk, 5, 18, 1.5)
    add_circle(sk, -5, 18, 1.5)


pad(tub, "TailPins", "YZ", TAIL_X + 0.5, 2.5, draw_tail_pins, reverse=True)

# Everything above started inside the floor. The diffuser cut trims it to the underside line.
pocket(tub, "DiffuserCut", "XZ", 0, None,
       lambda sk: add_poly(sk, [(KICK_X, Z_BOTTOM), (TAIL_X, KICK_Z), (-70, KICK_Z), (-70, 0), (KICK_X, 0)]))


# Strakes are wedges under the ramp, so they never poke up through the floor into the gear.
for strake_y in (20, 8, -8, -20):
    pad(tub, "Strake%+d" % strake_y, "XZ", -strake_y, 1.5,
        lambda sk: add_poly(sk, [(KICK_X, Z_BOTTOM), (TAIL_X, Z_BOTTOM), (TAIL_X, KICK_Z + 0.5), (KICK_X, Z_BOTTOM + 0.5)]),
        midplane=True)

# XZ sketch normal is -Y and a pocket cuts against the normal, so the +Y face needs reversing to cut inward.
for side, s in (("L", 1), ("R", -1)):
    pocket(tub, "Bearing" + side, "XZ", -29 * s, BEARING_T,
           lambda sk: add_circle(sk, X_REAR, AXLE_Z, BEARING_R + 0.05), reverse=s > 0)
    # v2: the side wall (up to Z_RAIL) crossed the bearing's way in by 0.5 mm. Clear the entry through the wall.
    pocket(tub, "BearingEntry" + side, "XZ", -29 * s, 31.6 - 29,
           lambda sk: add_circle(sk, X_REAR, AXLE_Z, BEARING_R + 0.05), reverse=s < 0)
    # Relief on the pocket floor so only the outer ring seats and the inner ring turns free.
    pocket(tub, "BearingRelief" + side, "XZ", -26 * s, 0.3,
           lambda sk: add_circle(sk, X_REAR, AXLE_Z, BEARING_RELIEF_R), reverse=s > 0)
pocket(tub, "AxleClearance", "XZ", 0, None, lambda sk: add_circle(sk, X_REAR, AXLE_Z, 2.0))


def draw_kingpins(sk):
    add_circle(sk, KP_X, KINGPIN_Y, 1.6)
    add_circle(sk, KP_X, -KINGPIN_Y, 1.6)


pocket(tub, "KingpinHoles", "XY", 0, None, draw_kingpins)
pocket(tub, "SwitchWindow", "XY", 0, None, lambda sk: add_rect(sk, 39, 49, 15, 18.6))
pocket(tub, "StrapSlot", "YZ", -45.0, 1.2, lambda sk: add_rect(sk, -8.2, -1.8, 20.9, 22.6))

# Heat-set insert holes, all open at the mating face.
insert_r = INSERT_M2[3] / 2
pocket(tub, "InsertHoleStrap", "XY", 21, INSERT_HOLE_DEPTH, lambda sk: add_circle(sk, STRAP_SCREW[0], STRAP_SCREW[1], insert_r))
pocket(tub, "InsertHolesTray", "XY", TRAY_Z, INSERT_HOLE_DEPTH, lambda sk: [add_circle(sk, x, y, insert_r) for x, y in TRAY_SCREWS])
pocket(tub, "InsertHolesRegulator", "XY", 11.5, INSERT_HOLE_DEPTH, lambda sk: [add_circle(sk, x, y, insert_r) for x, y in REG_SCREWS])
pocket(tub, "InsertHolesServo", "YZ", 16, INSERT_HOLE_DEPTH, lambda sk: [add_circle(sk, y, SERVO_HOLE_Z, insert_r) for y in SERVO_SCREWS])

SHELL_MAGS = [(8, 25.5), (8, -25.5), (-38, 26), (-38, -26)]
NOSE_MAGS = [(12, 12), (-12, 12)]    # (y, z)
TAIL_MAGS = [(12, 18), (-12, 18)]    # (y, z)
WING_MAGS = [(-70, 20), (-70, -20)]  # (x, y)
WING_SEAT_Z = 43.5
pocket_depth = MAG_T + 0.2
pocket(tub, "ShellMagnetPockets", "XY", Z_RAIL, pocket_depth,
       lambda sk: [add_circle(sk, x, y, MAG_R + MAG_CLEAR) for x, y in SHELL_MAGS])
pocket(tub, "NoseMagnetPockets", "YZ", NOSE_X, pocket_depth,
       lambda sk: [add_circle(sk, y, z, MAG_R + MAG_CLEAR) for y, z in NOSE_MAGS])
pocket(tub, "TailMagnetPockets", "YZ", TAIL_X, pocket_depth,
       lambda sk: [add_circle(sk, y, z, MAG_R + MAG_CLEAR) for y, z in TAIL_MAGS], reverse=True)

# Fillet the long side edges of the axle uprights: wheel loads bend them sideways, so these carry the stress.
notes = []
prev = tub.Tip
names = []
for i, e in enumerate(prev.Shape.Edges):
    bb = e.BoundBox
    in_upright = (bb.XMin > -53.1 and bb.XMax < -42.9 and 23.9 < min(abs(bb.YMin), abs(bb.YMax))
                  and max(abs(bb.YMin), abs(bb.YMax)) < 29.1)
    if in_upright and bb.XLength > 1 and bb.YMin * bb.YMax > 0 and abs(bb.Center.z - floor_top(bb.Center.x)) < 0.05:
        names.append("Edge%d" % (i + 1))
fil = tub.newObject("PartDesign::Fillet", "UprightFillets")
fil.Base = (prev, names)
fil.Radius = 1.0
doc.recompute()
if names and not fil.Shape.isNull() and fil.Shape.isValid() and "Invalid" not in fil.State:
    notes.append("upright fillets applied to %d edges, volume +%.1f mm3" % (len(names), fil.Shape.Volume - prev.Shape.Volume))
else:
    notes.append("upright fillets failed on %d edges and were removed" % len(names))
    doc.removeObject(fil.Name)
    tub.Tip = prev
    doc.recompute()


# ---------- Solid helpers ----------
def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def prism_xy(pts, z0, z1):
    wire = Part.makePolygon([V(x, y, z0) for x, y in pts] + [V(pts[0][0], pts[0][1], z0)])
    return Part.Face(wire).extrude(V(0, 0, z1 - z0))


def prism_xz(pts, y0, y1):
    wire = Part.makePolygon([V(x, y0, z) for x, z in pts] + [V(pts[0][0], y0, pts[0][1])])
    return Part.Face(wire).extrude(V(0, y1 - y0, 0))


def oval_y(x, z, rx, rz, y0, y1):
    pts = [V(x + rx * math.cos(2 * math.pi * k / 48), y0, z + rz * math.sin(2 * math.pi * k / 48)) for k in range(48)]
    curve = Part.BSplineCurve()
    curve.interpolate(pts, PeriodicFlag=True)
    return Part.Face(Part.Wire([curve.toShape()])).extrude(V(0, y1 - y0, 0))


def prism_yz(pts, x0, x1):
    wire = Part.makePolygon([V(x0, y, z) for y, z in pts] + [V(x0, pts[0][0], pts[0][1])])
    return Part.Face(wire).extrude(V(x1 - x0, 0, 0))


def cyl_y(x, z, r, y0, y1):
    return Part.makeCylinder(r, y1 - y0, V(x, y0, z), V(0, 1, 0))


def cyl_x(y, z, r, x0, x1):
    return Part.makeCylinder(r, x1 - x0, V(x0, y, z), V(1, 0, 0))


def cyl_z(x, y, r, z0, z1):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0), V(0, 0, 1))


def mirror_y(shape):
    return shape.mirror(V(0, 0, 0), V(0, 1, 0))


def both_sides(shape):
    return shape.fuse(mirror_y(shape))


def steered(shape, deg, side=1):
    out = shape.copy()
    out.rotate(V(KP_X, KINGPIN_Y * side, 0), V(0, 0, 1), deg)
    return out


def mesh_volume(shape, deviation=0.05):
    """Volume from the surface mesh. After a cut, Shape.Volume on these lofted surfaces read about 500 mm3 high."""
    pts, tris = shape.tessellate(deviation)
    return sum(pts[a].dot(pts[b].cross(pts[c])) for a, b, c in tris) / 6.0


def moved(shape, dx=0.0, dy=0.0, dz=0.0):
    out = shape.copy()
    out.translate(V(dx, dy, dz))
    return out


# ---------- DIVIDE: one master form, cut into shell, nose and tail, with canopy and wing as swaps ----------
def body_section(x, w, zb, ycr, zcr, zc, z0, t=0.0):
    w, zb, ycr, zcr, zc = w - t, zb - t, ycr - t, zcr - t, zc - t
    right = [V(x, w - 2, z0), V(x, w, zb), V(x, ycr, zcr), V(x, 0.6 * ycr, zc + 0.1 * (zcr - zc))]
    pts = right + [V(x, 0, zc)] + [V(x, -p.y, p.z) for p in reversed(right)]
    return Part.makePolygon(pts + [pts[0]])


def body_form(t, z0, x_min=-75.0, x_max=FACE_X):
    wires = [body_section(max(x_min, min(x_max, r[0])), r[1], r[2], r[3], r[4], r[5], z0, t) for r in BODY]
    return Part.makeLoft(wires, True, True)


def canopy_form(t, base):
    wires = []
    for x, a, r, top in CANOPY:
        belt = min(CABIN_BELT, top - t - 3)
        right = [V(x, a - t, base), V(x, a - t, belt), V(x, r - t, top - t - 2), V(x, r - t - 3, top - t)]
        pts = right + [V(x, -p.y, p.z) for p in reversed(right)]
        wires.append(Part.makePolygon(pts + [pts[0]]))
    return Part.makeLoft(wires, True, True)


master = body_form(0.0, BODY_Z0)
cavity = body_form(WALL, 0.0, -75 + WALL, FACE_X - WALL)

# Wheel openings are cut from the master, so shell, nose and splitter inherit them.
sweep_one = cyl_y(X_FRONT, AXLE_Z, WHEEL_R + 1.5, FRONT_IN - 2, FRONT_OUT + 8)
sweep = sweep_one.copy()
for a in (-OUTER_DEG, -OUTER_DEG / 2, STEER_DEG / 2, STEER_DEG):  # left wheel: inner lock left, outer lock right
    sweep = sweep.fuse(steered(sweep_one, a))
# The swept volume only cuts inboard, hidden under the fender. The visible opening is one clean oval.
sweep = both_sides(sweep.common(box(0, 100, 0, 34, -10, 60)))
front_arches = both_sides(oval_y(X_FRONT, AXLE_Z, 22.5, 19.0, FRONT_IN, 60))
arches = both_sides(cyl_y(X_REAR, AXLE_Z, WHEEL_R + 2.5, REAR_IN - 1.5, 60))
intake = both_sides(prism_xz([(-23, 15), (-28, 15), (-28, 36), (-24, 36)], 36, 60))  # the tall side vent ahead of the rear wheel


def checked_cut(base, tool, label):
    """Boolean results here can depend on earlier operations, so cut a clean copy and refuse a bad result.
    Judged on volume: BoundBox on these ruled faces reports the untrimmed surface, not the part."""
    expected = base.Volume - base.copy().common(tool).Volume
    for attempt in (lambda: base.copy().cut(tool), lambda: base.copy().cut(tool, 0.001)):
        result = attempt()
        actual = mesh_volume(result)
        if result.isValid() and len(result.Solids) == 1 and abs(actual - expected) <= 0.02 * expected:
            return result
    raise RuntimeError("%s: cut gave a bad body (valid=%s, solids=%d, volume %.0f, expected %.0f)" % (label, result.isValid(), len(result.Solids), actual, expected))


outer = checked_cut(master, sweep.fuse([front_arches, arches, intake]), "wheel and intake openings")
skin = checked_cut(outer, cavity.common(box(-80, 80, -60, 60, BODY_Z0 - 1, 80)), "body hollow")

head_cut = both_sides(box(FACE_X - 2.5, 80, 28, 41, 28, 33))        # rectangular headlights, as traced
bezel_cut = both_sides(box(FACE_X - 2.5, 80, 27, 42, 27, 33.8))
fog_cut = both_sides(box(FACE_X - 2.5, 80, 34, 41, 20, 24))
tail_light_cut = both_sides(box(-76, -73, 16, 40, 33, 40))
SPLITTER_MAGS = [(63.5, 22.3), (63.5, -22.3)]
SPLITTER_PINS = [(63.5, 27.8), (63.5, -27.8)]
SPLITTER_Z = (5.5, BODY_Z0)   # 1 mm below the tub floor, ramped up at the front so it rides over bumps
SPLITTER_IFACE = 8.5          # magnets meet here: bosses on the splitter rise through the open underside of the nose
SPLITTER_TIP_X = 76.5

# Cabin: body-colour shell with real pillars, and a dark glass liner showing through the window openings.
canopy_outer = canopy_form(0.0, CANOPY_BASE)
canopy_inner = canopy_form(WALL, CANOPY_BASE - 3)
canopy = canopy_outer.cut(canopy_inner).cut(master)
CANOPY_LEDGE_TOP = 25.5
posts = [cyl_z(CANOPY_SCREW[0], s * CANOPY_SCREW[1], 2.9, CANOPY_LEDGE_TOP, 75).common(canopy_outer) for s in (1, -1)]
canopy = canopy.fuse(posts).removeSplitter()
# Window openings traced from the side view.
side_windows = both_sides(prism_xz([(trace_x(440), 43.5), (trace_x(495), trace_z(52)), (trace_x(615), trace_z(52)), (trace_x(615), 43.5)], 20, 60)).fuse(
    both_sides(prism_xz([(trace_x(637), 43.5), (trace_x(640), trace_z(52)), (trace_x(695), trace_z(52)), (trace_x(775), 44.5), (trace_x(760), 43.5)], 20, 60)))
windshield = prism_yz([(-32, 43.5), (32, 43.5), (25, 57.5), (-25, 57.5)], 4, 34)  # starts ahead of the cabin screw posts
rear_window = prism_yz([(-29, 47.5), (29, 47.5), (24, 57.5), (-24, 57.5)], -70, -38)
canopy = canopy.cut(side_windows).cut(windshield).cut(rear_window)
for s in (1, -1):
    canopy = canopy.cut(cyl_z(CANOPY_SCREW[0], s * CANOPY_SCREW[1], insert_r, CANOPY_LEDGE_TOP, CANOPY_LEDGE_TOP + INSERT_HOLE_DEPTH))
GLASS_GAP = 0.15  # fit gap to the cabin wall: the liner has to slide in, and coincident faces break the boolean
glass = canopy_form(WALL + GLASS_GAP, CANOPY_BASE - 3).cut(canopy_form(WALL + GLASS_GAP + 1.0, CANOPY_BASE - 3)).cut(master)
for s in (1, -1):
    glass = glass.cut(cyl_z(CANOPY_SCREW[0], s * CANOPY_SCREW[1], 3.2, 20, 80))

# Shell: nose seam at x=58, tail seam at x=-62, lifts straight off the tub.
shell = skin.common(box(TAIL_X, NOSE_X, -60, 60, 0, 80))
pillars = []
for x0, x1, y0, y1 in ((-3, 13, 23, 29), (-42.5, -33.5, 23, 29)):
    for s in (1, -1):
        pillars.append(box(x0, x1, min(s * y0, s * y1), max(s * y0, s * y1), Z_RAIL, 80).common(outer))
opening = prism_xy(ROOF_OPENING, 20, 80)  # planar walls cross the body cleanly, and the pillars stay tied to the skin
shell_solid = shell.fuse(pillars).removeSplitter()
shell = shell_solid.cut(opening)
canopy_cut_expected = shell_solid.Volume - shell_solid.common(opening).Volume
canopy_cut_actual = mesh_volume(shell)
canopy_leftover = shell.common(opening).Volume
for x, y in SHELL_MAGS:
    shell = shell.cut(cyl_z(x, y, MAG_R + MAG_CLEAR, Z_RAIL, Z_RAIL + pocket_depth))
for s in (1, -1):
    shell = shell.cut(cyl_z(0, 25.5 * s, 2.2, Z_RAIL, Z_RAIL + 2.5))
for s in (1, -1):
    ledge = box(-3, 3, min(s * 14.5, s * 23), max(s * 14.5, s * 23), CANOPY_LEDGE_TOP - 2, CANOPY_LEDGE_TOP)
    shell = shell.fuse(ledge.cut(cyl_z(CANOPY_SCREW[0], s * CANOPY_SCREW[1], CLEAR_M2, 20, 30)))
shell = shell.removeSplitter()
vents = both_sides(prism_xy([(37, 8), (37, 21), (31, 21), (31, 8)], 15, 60))  # hood louvres, as traced from the top view
shell = shell.cut(vents)

# Dark inserts behind the hood louvres and side vents hide the wiring and keep dust out. Glued inside the shell.
inside_shell = body_form(WALL + 0.15, 0.0, -75 + WALL, FACE_X - WALL)  # plates follow the real inner surface with a fit gap
vent_hood = box(29.5, 38.5, 6.5, 22.5, 38.1, 39.0).common(inside_shell)
for x in (32.2, 34, 35.8):
    vent_hood = vent_hood.fuse(box(x - 0.4, x + 0.4, 8.2, 20.8, 38.9, 40.3))
vent_hood = vent_hood.removeSplitter()
vent_side = box(-29.2, -21.5, 37.2, 38, 13.5, 37.6).common(inside_shell)
for z in (19, 24, 29):
    vent_side = vent_side.fuse(box(-27.7, -24.3, 37.9, 42.2, z, z + 1))
vent_side = vent_side.removeSplitter().common(outer)
vent_parts = {"VentHoodL": vent_hood, "VentHoodR": mirror_y(vent_hood), "VentSideL": vent_side, "VentSideR": mirror_y(vent_side)}

# Nose with splitter: locates on the tub shelf, held by magnets, swappable for a TPU crash version.
nose_skin = skin.common(box(NOSE_X, 76, -60, 60, 0, 80))
nose_back = box(NOSE_X, NOSE_X + 3, -20, 20, Z_BOTTOM + FLOOR_T, 80).common(outer)
# Pads inside the nose take the splitter magnets and pins, tied to the front wall and side wall.
nose_pads = []
for s in (1, -1):
    for x0, x1, y0, y1, z0, z1 in ((60, 67, 18.6, 30, SPLITTER_IFACE, 11), (67, FACE_X - 1.4, 18.6, 30, SPLITTER_IFACE, 9.5), (64, 66, 30, 44, SPLITTER_IFACE, 10.5)):
        nose_pads.append(box(x0, x1, min(s * y0, s * y1), max(s * y0, s * y1), z0, z1).common(outer))
nose = nose_skin.fuse([nose_back] + nose_pads).removeSplitter()
nose = nose.cut(box(NOSE_X - 1, SHELF_X + 0.2, -18.2, 18.2, Z_BOTTOM - 1, Z_BOTTOM + FLOOR_T))
for y, z in NOSE_MAGS:
    nose = nose.cut(cyl_x(y, z, MAG_R + MAG_CLEAR, NOSE_X, NOSE_X + pocket_depth))
UPPER_GRILLE = [(-26.5, 32), (26.5, 32), (26.5, 26.5), (-26.5, 26.5)]
LOWER_INTAKE = [(-30, 23), (30, 23), (28, 16), (-28, 16)]
nose = nose.cut(prism_yz(UPPER_GRILLE, FACE_X - 2, FACE_X + 1)).cut(prism_yz(LOWER_INTAKE, FACE_X - 2, FACE_X + 1))
head_lights = skin.common(head_cut)
head_bezels = skin.common(bezel_cut).cut(head_cut)
fog_lights = skin.common(fog_cut)
nose = nose.cut(bezel_cut).cut(fog_cut)
for x, y in SPLITTER_MAGS:
    nose = nose.cut(cyl_z(x, y, MAG_R + MAG_CLEAR, SPLITTER_IFACE, SPLITTER_IFACE + pocket_depth))
for x, y in SPLITTER_PINS:
    nose = nose.cut(cyl_z(x, y, 1.7, SPLITTER_IFACE, SPLITTER_IFACE + 2))

# Grille: dark insert behind the openings, glued in from inside the nose.
plate_x = FACE_X - 2.8
grille = box(plate_x, plate_x + 1.1, -31.5, 31.5, 15.5, 32.4)
for z in (27.3, 29.2):
    grille = grille.fuse(box(plate_x + 1.0, plate_x + 2.5, -26.2, 26.2, z, z + 0.9))
for z in (17.3, 19.3, 21.3):
    half = 28 + (z - 16) * 2 / 7 - 0.2
    grille = grille.fuse(box(plate_x + 1.0, plate_x + 2.5, -half, half, z, z + 0.9))
grille = grille.removeSplitter()

# Splitter: the big traced wedge, a separate dark part on two magnets. Two pins take the crash load so it pops off, not snaps.
splitter = prism_xy([(59, -30), (67, -46.5), (74, -46.5), (SPLITTER_TIP_X, -36), (SPLITTER_TIP_X, 36), (74, 46.5), (67, 46.5), (59, 30)],
                    SPLITTER_Z[0], SPLITTER_Z[1]).cut(sweep).cut(front_arches)
splitter = splitter.cut(box(NOSE_X - 1, SHELF_X + 0.2, -18.2, 18.2, Z_BOTTOM - 2, Z_BOTTOM + FLOOR_T))
wedge = prism_xz([(FACE_X, BODY_Z0), (SPLITTER_TIP_X, BODY_Z0), (SPLITTER_TIP_X, 8.5), (FACE_X, 15)], -44, 44)
splitter = splitter.fuse([wedge, box(69, 75, 44.6, 46, BODY_Z0, 14), box(69, 75, -46, -44.6, BODY_Z0, 14)]
                         + [cyl_z(x, y, 4.1, BODY_Z0 - 0.5, SPLITTER_IFACE) for x, y in SPLITTER_MAGS]
                         + [cyl_z(x, y, 3.0, BODY_Z0 - 0.5, SPLITTER_IFACE) for x, y in SPLITTER_PINS]
                         + [cyl_z(x, y, 1.5, SPLITTER_IFACE - 0.5, SPLITTER_IFACE + 1.8) for x, y in SPLITTER_PINS]).removeSplitter()
for x, y in SPLITTER_MAGS:
    splitter = splitter.cut(cyl_z(x, y, MAG_R + MAG_CLEAR, SPLITTER_IFACE - pocket_depth, SPLITTER_IFACE))
splitter = splitter.cut(prism_xz([(71, SPLITTER_Z[0]), (77, BODY_Z0 + 0.1), (77, 4), (71, 4)], -50, 50))  # ramp

# Tail: carries the rear lights and the diffuser exit, and gives the wing its magnet seats.
# Window first, then hollow: taking this section from the finished skin returns nothing on these ruled faces.
tail_skin = checked_cut(outer.common(box(-76, TAIL_X, -60, 60, KICK_Z, 80)), cavity, "tail hollow")
tail_block = box(TAIL_X - 3, TAIL_X, -20, 20, KICK_Z, 80).common(outer)
bosses = [box(x - 4, x + 4, y - 4, y + 4, 26, 80).common(outer) for x, y in WING_MAGS]
tail = tail_skin.fuse([tail_block] + bosses).removeSplitter()
tail = tail.cut(box(-76, -70, -32, 32, KICK_Z, 17))
for y, z in TAIL_MAGS:
    tail = tail.cut(cyl_x(y, z, MAG_R + MAG_CLEAR, TAIL_X - pocket_depth, TAIL_X))
for y in (5, -5):
    tail = tail.cut(cyl_x(y, 18, 1.7, TAIL_X - 2.5, TAIL_X))
tail_lights = tail_skin.common(tail_light_cut)
tail = tail.cut(tail_light_cut)

# Wing: separate swappable part on magnets, so it can print flat with no supports under the blade.
foot = both_sides(box(-74, -66, 16, 24, WING_SEAT_Z, WING_SEAT_Z + 4.2))
tail = tail.cut(foot)
for x, y in WING_MAGS:
    tail = tail.cut(cyl_z(x, y, MAG_R + MAG_CLEAR, WING_SEAT_Z - pocket_depth, WING_SEAT_Z))
# The big steep wing, traced from the side view.
blade = prism_xz([(-62, 53.8), (-68, 58.6), (-75, 63.4), (-75, 61.9), (-68, 57)], -43, 43)
plate = prism_xz([(-62, 52.5), (-69, 61), (-75, 64.5), (-75, 56), (-72, 51)], 41.4, 43)
pylon = prism_xz([(-73, 47.2), (-67, 47.2), (-66.5, 56.5), (-72, 61)], 18.5, 21.5)
wing = blade.fuse([plate, mirror_y(plate), pylon, mirror_y(pylon), foot]).removeSplitter()
for x, y in WING_MAGS:
    wing = wing.cut(cyl_z(x, y, MAG_R + MAG_CLEAR, WING_SEAT_Z, WING_SEAT_Z + pocket_depth))


# ---------- Moving parts ----------
KNUCKLE_FACE_Y = FRONT_IN - 0.5
TIRE_STRETCH = 0.3       # TPU tyre bore is this much under the rim: stretch it on, then a drop of CA
D_SHAFT = (3.0, 2.5)     # rear axle: 3 mm D-profile shaft, 2.5 mm across the flat
FRONT_HUB_END = KNUCKLE_FACE_Y + AX_SPACER[2] - 0.2   # wheel hub ends 0.2 short of the spacer: end play, no clamp


def d_profile_y(x, z, d, flat, y0, y1, grow=0.0):
    """D shaft or D bore along Y. The flat faces +Z."""
    r = d / 2 + grow
    return cyl_y(x, z, r, y0, y1).common(box(x - r - 1, x + r + 1, y0 - 1, y1 + 1, z - r - 1, z + (flat - d / 2) + grow))


def make_wheel(x, y_in, y_out, front):
    """Returns (tyre, rim). Front rims spin on a round spacer; rear rims press on the D shaft."""
    rim_r = WHEEL_R - 4.5
    tire = cyl_y(x, AXLE_Z, WHEEL_R, y_in, y_out)
    tire = tire.makeFillet(2.0, tire.Edges)
    tire = tire.cut(cyl_y(x, AXLE_Z, rim_r - TIRE_STRETCH, y_in - 1, y_out + 1))
    rim = cyl_y(x, AXLE_Z, rim_r, y_in, y_out).cut(cyl_y(x, AXLE_Z, rim_r - 0.8, y_out - 1.5, y_out + 1))
    window_r0 = 5.2 if front else 3.4
    window_r1, half = rim_r - 1.4, math.radians(23 if front else 23)
    sector = [(window_r0 * math.cos(a), window_r0 * math.sin(a)) for a in (-half * 0.6, half * 0.6)]
    sector += [(window_r1 * math.cos(a), window_r1 * math.sin(a)) for a in (half, half / 2, 0, -half / 2, -half)]
    window = prism_xz([(x + u, AXLE_Z + v) for u, v in sector], y_in - 1, y_out + 1)
    for k in range(5):
        w = window.copy()
        w.rotate(V(x, 0, AXLE_Z), V(0, 1, 0), 72 * k)
        rim = rim.cut(w)
    if front:
        rim = rim.cut(cyl_y(x, AXLE_Z, AX_SPACER[0] / 2 + 0.1, y_in - 1, y_out + 1))   # runs on the spacer
        rim = rim.cut(cyl_y(x, AXLE_Z, 4.0, FRONT_HUB_END, y_out + 1))                # washer and screw head sit in here
    else:
        rim = rim.cut(d_profile_y(x, AXLE_Z, D_SHAFT[0], D_SHAFT[1], y_in - 1, y_out + 1))  # press on, then CA
    return tire, rim


tire_f, rim_f = make_wheel(X_FRONT, FRONT_IN, FRONT_OUT, front=True)
tire_r, rim_r_ = make_wheel(X_REAR, REAR_IN, REAR_OUT, front=False)
wheel_f = tire_f.fuse(rim_f)

# Knuckle: turns on a round spacer clamped between the ear insert and the kingpin screw.
ARM_Z = (18.5, 20.5)   # high enough that the lock nut under the tip clears the floor switch at full lock
KN_Z = (EAR_TOP + 0.25, EAR_TOP + KP_SPACER[2] - 0.25)
arm_dx, arm_dy = ARM_TIP[0] - KP_X, ARM_TIP[1] - KINGPIN_Y
arm_len = math.hypot(arm_dx, arm_dy)
nx, ny = -arm_dy / arm_len * 2.2, arm_dx / arm_len * 2.2
arm = prism_xy([(KP_X + nx, KINGPIN_Y + ny), (ARM_TIP[0] + nx, ARM_TIP[1] + ny), (ARM_TIP[0] - nx, ARM_TIP[1] - ny),
                (KP_X - nx, KINGPIN_Y - ny)], *ARM_Z).fuse(cyl_z(ARM_TIP[0], ARM_TIP[1], 2.75, *ARM_Z))
knuckle = cyl_z(KP_X, KINGPIN_Y, 4.2, *KN_Z).fuse(
    [box(X_FRONT - 3.7, KP_X, KINGPIN_Y - 1.5, KNUCKLE_FACE_Y, *KN_Z), arm]).removeSplitter()
knuckle = knuckle.cut(cyl_z(KP_X, KINGPIN_Y, KP_SPACER[0] / 2 + 0.1, KN_Z[0] - 1, KN_Z[1] + 1))
knuckle = knuckle.cut(cyl_z(ARM_TIP[0], ARM_TIP[1], CLEAR_M2, ARM_Z[0] - 1, ARM_Z[1] + 1))
# Clear the tie-rod end above the arm and the lock nut below it: they turn about the tip pin relative to the knuckle.
knuckle = knuckle.cut(cyl_z(ARM_TIP[0], ARM_TIP[1], 3.3, ARM_Z[1], KN_Z[1] + 1)).cut(cyl_z(ARM_TIP[0], ARM_TIP[1], 3.3, KN_Z[0] - 1, ARM_Z[0]))
knuckle = knuckle.cut(cyl_y(X_FRONT, AXLE_Z, INSERT_M3[3] / 2, KNUCKLE_FACE_Y - INSERT_HOLE_DEPTH, KNUCKLE_FACE_Y + 0.5))
knuckle = knuckle.cut(cyl_y(X_FRONT, AXLE_Z, 1.65, KNUCKLE_FACE_Y - 4.6, KNUCKLE_FACE_Y))  # room for the screw tip
results_notes_kn = "kingpin bore to insert hole wall %.2f mm" % (KP_TRAIL - KP_SPACER[0] / 2 - 0.1 - INSERT_M3[3] / 2)

# Tie rod: bar between the arm tips, a bridge over the pin's lock nut, and a tab with the vertical slot.
TX, TY = ARM_TIP
TR_Z, TR_HI = (20.5, 23.0), (24.4, 26.9)
TAB_X0, TAB_X1 = 32.9, 36.4
tr_half = box(TX - 1.5, TX + 1.5, 8.5, TY, *TR_Z).fuse([cyl_z(TX, TY, 2.75, *TR_Z), box(TX - 1.5, TX + 1.5, 7.0, 8.5, TR_Z[0], TR_HI[1])])
tie_rod = both_sides(tr_half).fuse([box(TAB_X0, TX + 1.5, -8.5, 8.5, *TR_HI), box(TAB_X0, TAB_X1, -3.5, 3.5, 16.6, TR_HI[1])]).removeSplitter()
for s in (1, -1):
    tie_rod = tie_rod.cut(cyl_z(TX, s * TY, CLEAR_M2, TR_Z[0] - 1, TR_Z[1] + 1))
tie_rod = tie_rod.cut(box(TAB_X0 - 1, TAB_X1 + 1, -SLOT_HALF_W, SLOT_HALF_W, SLOT_Z[0], SLOT_Z[1]))
tie_rod = tie_rod.removeSplitter()


def rod_at(shape, inner_deg, turn):
    """Move a shape that rides on the tie rod to the rod pose for this steering input."""
    l, r, dy, dx, yaw, horn = steer_pose(inner_deg, turn)
    out = shape.copy()
    out.rotate(V(TX, 0, 0), V(0, 0, 1), yaw)
    out.translate(V(dx, dy, 0))
    return out


# Rear axle: 3 mm round shaft (file a 0.5 mm flat at each wheel and under the gear set screw) in two 683ZZ bearings.
# A 4 mm round spacer between each bearing's inner ring and the wheel hub locates it: no collars needed.
AXLE_LEN = 2 * REAR_OUT
axle = d_profile_y(X_REAR, AXLE_Z, D_SHAFT[0], D_SHAFT[1], -REAR_OUT, REAR_OUT)
bearing = cyl_y(X_REAR, AXLE_Z, BEARING_R, 26, 29).cut(cyl_y(X_REAR, AXLE_Z, 1.5, 26, 29))
rear_spacer = cyl_y(X_REAR, AXLE_Z, REAR_SPACER[0] / 2, 29, 29 + REAR_SPACER[2]).cut(cyl_y(X_REAR, AXLE_Z, REAR_SPACER[1] / 2, 28, 34))


# ---------- Gears: real involute teeth ----------
def _inv(a):
    return math.tan(a) - a


def gear_outline(z, m, x, tip_red=0.0, backlash=0.0, alpha_deg=20.0, npts=14):
    """2D outline of an external involute spur gear with profile shift, as (u, v) points."""
    alpha = math.radians(alpha_deg)
    r = m * z / 2.0
    rb = r * math.cos(alpha)
    ra = r + m * (1 + x) - tip_red
    rf = r - m * (1.25 - x)
    s = m * (math.pi / 2 + 2 * x * math.tan(alpha)) - backlash
    psi = s / (2 * r)

    def half_angle(rho):
        if rho <= rb:
            return psi + _inv(alpha)
        return psi + _inv(alpha) - _inv(math.acos(rb / rho))
    r_start = max(rf, rb)
    radii = [r_start + (ra - r_start) * i / (npts - 1) for i in range(npts)]
    flank = ([(rf, half_angle(rb))] if rf < rb else []) + [(rho, half_angle(rho)) for rho in radii]
    pitch = 2 * math.pi / z
    pts = []
    for k in range(z):
        c = k * pitch
        up = [(rho, c - h) for rho, h in flank]
        tip = [(ra, (c - flank[-1][1]) + 2 * flank[-1][1] * i / 4) for i in range(1, 4)]
        down = [(rho, c + h) for rho, h in reversed(flank)]
        a0, a1 = c + flank[0][1], (k + 1) * pitch - flank[0][1]
        root = [(rf, a0 + (a1 - a0) * i / 4) for i in range(1, 4)]
        pts += [(rho * math.cos(a), rho * math.sin(a)) for rho, a in up + tip + down + root]
    return pts, dict(r=r, ra=ra, rf=rf)


def gear_pair(m, z1, z2, centre, x1):
    """Shift x1 on the pinion; x2 and the tip reduction follow from the centre distance."""
    alpha = math.radians(20.0)
    a0 = m * (z1 + z2) / 2
    aw = math.acos(a0 * math.cos(alpha) / centre)
    xsum = (z1 + z2) * (_inv(aw) - _inv(alpha)) / (2 * math.tan(alpha))
    k = xsum - (centre - a0) / m
    return dict(m=m, z1=z1, z2=z2, x1=x1, x2=xsum - x1, tip_red=k * m, centre=centre)


def gear_solid_y(pts, cx, cz, y0, y1, turn_deg=0.0):
    wire = Part.makePolygon([V(cx + u, y0, cz + v) for u, v in pts] + [V(cx + pts[0][0], y0, cz + pts[0][1])])
    solid = Part.Face(wire).extrude(V(0, y1 - y0, 0))
    if turn_deg:
        solid.rotate(V(cx, 0, cz), V(0, 1, 0), turn_deg)
    return solid


GEAR_CENTRE = 9.0
MOTOR_X = X_REAR + GEAR_CENTRE      # motor shaft x, fixed by the cradle walls
# Default drive: bought 0.5-module brass gears (N20 style), 12T pinion with a 3 mm D bore, 24T with 3 mm bore and set screw.
GEARS = gear_pair(0.5, 12, 24, GEAR_CENTRE, 0.0)
GEAR_FACE = (8.0, 12.0)             # tooth faces, y
pin_pts, pin_d = gear_outline(12, 0.5, 0.0, backlash=0.04)
gear_pts, gear_d = gear_outline(24, 0.5, 0.0, backlash=0.04)
pinion = gear_solid_y(pin_pts, MOTOR_X, AXLE_Z, *GEAR_FACE).cut(d_profile_y(MOTOR_X, AXLE_Z, 3.0, 2.5, 7, 13))
gear = gear_solid_y(gear_pts, X_REAR, AXLE_Z, *GEAR_FACE, turn_deg=180.0 / 24).fuse(
    cyl_y(X_REAR, AXLE_Z, 4.0, GEAR_FACE[1], GEAR_FACE[1] + 4.0)).cut(cyl_y(X_REAR, AXLE_Z, 1.5, 7, 17))
gear = gear.removeSplitter()

# Backup drive: printed 0.6-module 12T/17T pair at the same 9.0 mm centres (1.42:1, faster, needs a fine nozzle or resin).
ALT = gear_pair(0.6, 12, 17, GEAR_CENTRE, 0.32)
alt_p_pts, alt_p = gear_outline(12, 0.6, ALT["x1"], ALT["tip_red"], backlash=0.06)
alt_g_pts, alt_g = gear_outline(17, 0.6, ALT["x2"], ALT["tip_red"], backlash=0.06)
alt_pinion = gear_solid_y(alt_p_pts, 0, 0, 0, 5.0).cut(d_profile_y(0, 0, 3.0, 2.5, -1, 6, grow=0.05))
alt_gear = gear_solid_y(alt_g_pts, 0, 0, 0, 5.0).fuse(cyl_y(0, 0, 3.6, 5.0, 9.0)).cut(d_profile_y(0, 0, 3.0, 2.5, -1, 10, grow=0.05))
alt_gear = alt_gear.removeSplitter()
for shp in (alt_pinion, alt_gear):  # print flat: tooth faces on the bed
    shp.rotate(V(0, 0, 0), V(1, 0, 0), 90)

# ---------- Bought parts: placeholder sizes, confirm against real parts ----------
# Pololu HPCB micro metal gearmotor: 10 x 12 x 25 mm, 3 mm D shaft 9 mm long.
motor = box(MOTOR_X - 6, MOTOR_X + 6, -18, 7, 11, 21).fuse(d_profile_y(MOTOR_X, AXLE_Z, 3.0, 2.5, 7, 16))
battery = box(-26.8, -6.8, -20, 20, Z_BOTTOM + FLOOR_T, Z_BOTTOM + FLOOR_T + 12)  # Gens Ace 300 mAh 2S 45C: 40 x 20 x 12

# Printed tray, on two M2 screws, with the Nano on four M1.6 screws. Lift it out and the battery is free.
tray = box(-32.9, 15, -10.5, 10.5, TRAY_Z, TRAY_Z + 1.5).fuse(
    [box(-33.4, -27.6, 8, 14, TRAY_Z, TRAY_Z + 1.5), box(-6.6, -0.8, -13.3, -8, TRAY_Z, TRAY_Z + 1.5)])
NANO_Z = TRAY_Z + 3.5  # 2 mm bosses leave room for solder tails under the board
tray = tray.fuse([cyl_z(x, y, 2, TRAY_Z + 1.5, NANO_Z) for x, y in NANO_HOLES]).removeSplitter()
for x, y in TRAY_SCREWS:
    tray = tray.cut(cyl_z(x, y, CLEAR_M2, TRAY_Z - 1, TRAY_Z + 2))
for x, y in NANO_HOLES:
    tray = tray.cut(cyl_z(x, y, 0.65, TRAY_Z - 1, NANO_Z + 1))  # pilot, the M1.6 screw self-taps: no M1.6 insert listed

nano = box(NANO_X0, NANO_X0 + 43.16, -8.88, 8.88, NANO_Z, NANO_Z + 1.0)
for x, y in NANO_HOLES:
    nano = nano.cut(cyl_z(x, y, 0.825, NANO_Z - 1, NANO_Z + 2))
nano = nano.fuse([box(NANO_X0 + 5, NANO_X0 + 38, -6.2, 6.2, NANO_Z + 1, NANO_Z + 3.5),
                  box(NANO_X0 - 1.5, NANO_X0 + 5, -4, 4, NANO_Z + 1, NANO_Z + 4)]).removeSplitter()

servo_y = SERVO_Y
servo = box(0, 22.7, servo_y - 11.1, servo_y + 11.1, 8.5, 20.3).fuse(  # SG90: 22.2 x 11.8, 32.2 over the flange
    [box(16, 18.5, servo_y - 16.1, servo_y + 16.1, 8.5, 20.3), cyl_x(0, SERVO_HOLE_Z, 2.4, 22.7, 29)]).removeSplitter()
for y in SERVO_SCREWS:
    servo = servo.cut(cyl_x(y, SERVO_HOLE_Z, CLEAR_M2, 15, 19))
# SG90 single-arm horn: drill the hole at HORN_R to 1.6 mm; the M2 pin threads into it.
horn = box(29, 31, -2.2, 2.2, HORN_AXIS[1] - 3.5, PIN_Z0 + 2.2).fuse(cyl_x(HORN_AXIS[0], HORN_AXIS[1], 3.5, 29, 31)).removeSplitter()
horn = horn.cut(cyl_x(HORN_AXIS[0], PIN_Z0, 0.8, 28, 32))

driver = box(33.7, 54, 0.5, 13.2, 9.5, 12.87)   # Pololu DRV8833 carrier: no mounting holes, foam tape on the floor
level_shifter = box(3, 16, -11, -1, 20.7, 22.7)  # Pololu 4-channel shifter 13 x 10 x 2: no holes, tape on the servo
regulator = box(36, 53.8, -19, -1.2, 11.5, 13.1)  # Pololu D24V22F5 board
for x, y in REG_SCREWS:
    regulator = regulator.cut(cyl_z(x, y, 1.09, 11, 14))
regulator = regulator.fuse(box(41, 49, -16, -4, 13.1, 19.5)).removeSplitter()  # components, 8 mm overall
# Pololu #2810 MOSFET switch, 3 A continuous, taped to the wall. The slide switch below only carries its small control signal.
power_board = box(51.5, 54, -7.6, 7.6, 16, 31.2)  # 15.2 x 15.2, parts facing back, foam tape on the front wall
power_switch = box(34, 53.7, 14, 19.6, 8.5, 15.5).fuse(  # SS-12F15 slide switch, glued in its pocket: holes unconfirmed
    [box(43, 45, 16, 17.6, 6.5, 8.5), box(41, 47, 16, 17.6, 15.5, 18.5)]).removeSplitter()

magnets = []
for x, y in SHELL_MAGS:
    magnets.append(cyl_z(x, y, MAG_R, Z_RAIL - MAG_T, Z_RAIL))
    magnets.append(cyl_z(x, y, MAG_R, Z_RAIL, Z_RAIL + MAG_T))
for y, z in NOSE_MAGS:
    magnets.append(cyl_x(y, z, MAG_R, NOSE_X - MAG_T, NOSE_X))
    magnets.append(cyl_x(y, z, MAG_R, NOSE_X, NOSE_X + MAG_T))
for y, z in TAIL_MAGS:
    magnets.append(cyl_x(y, z, MAG_R, TAIL_X, TAIL_X + MAG_T))
    magnets.append(cyl_x(y, z, MAG_R, TAIL_X - MAG_T, TAIL_X))
for x, y in SPLITTER_MAGS:
    magnets.append(cyl_z(x, y, MAG_R, SPLITTER_IFACE - MAG_T, SPLITTER_IFACE))
    magnets.append(cyl_z(x, y, MAG_R, SPLITTER_IFACE, SPLITTER_IFACE + MAG_T))
for x, y in WING_MAGS:
    magnets.append(cyl_z(x, y, MAG_R, WING_SEAT_Z - MAG_T, WING_SEAT_Z))
    magnets.append(cyl_z(x, y, MAG_R, WING_SEAT_Z, WING_SEAT_Z + MAG_T))
magnets = Part.makeCompound(magnets)

# ---------- Wiring: real routes as solid bundles, so they get clash-checked like any other part ----------
# Radius assumes silicone wire: about 1.4 mm OD at 26 AWG power, 0.9 mm OD at 30 AWG signal.
WIRE_ROUTES = {
    "Wires_MotorToDriver": (1.5, [(-39, -20, 16), (-39, -20.5, 17), (-30, -21, 24), (-6, -21, 24), (-4.5, -21, 21.5), (8, -21, 21), (9.8, -21, 22.4),
                                  (26, -14, 22.5), (30, -12, 16.5), (34.5, -5, 14.6), (34.5, 1, 14.4)]),
    "Wires_BatteryToSwitch": (1.7, [(-5, 17, 17), (-2, 17, 17), (12, 15, 16), (28, 12.2, 17), (49.5, 12.2, 17), (49.8, 7, 17.5)]),
    "Wires_PowerBoardToDriver": (1.7, [(49.8, 3, 17.5), (49.8, 3, 14.6)]),
    "Wires_PowerBoardToRegulator": (1.0, [(50.5, -2, 17.5), (48, -2.5, 14.3)]),
    "Wires_SwitchToPowerBoard": (0.8, [(48, 15, 16.3), (49, 14.5, 21), (50.6, 8.2, 22)]),
    "Wires_PowerBoardToNanoVIN": (1.5, [(50, 5, 20.5), (50, 5, 29.5), (20, 7, 30), (15.7, 9, 31)]),
    "Wires_RegulatorToServo": (1.5, [(34.4, -8, 13), (33, -8, 15), (30, -9, 17.5), (25, -9, 22), (17.7, -6.5, 22.9)]),
    "Wires_NanoToShifter": (1.5, [(15.7, -7, 31.5), (17, -6, 27), (17.6, -4, 22.9)]),
    "Wires_ServoCable": (1.75, [(-1.8, -5, 14.5), (-1.8, -5, 22), (1.2, -6, 22.6)]),
    "Wires_DriverToNano": (1.5, [(36, 9, 14.5), (30, 8, 16.5), (26, 8, 20), (24, 7, 23), (19, 6, 26), (17, 4, 28), (15.7, 2, 31)]),
}
WIRE_ENDS = {  # parts each route is meant to touch; only ignored in the fatter-wire margin test
    "Wires_MotorToDriver": {"Motor_N20", "Driver"}, "Wires_BatteryToSwitch": {"Battery_2S", "PowerSwitch", "PowerBoard"},
    "Wires_PowerBoardToDriver": {"PowerSwitch", "PowerBoard", "Driver"}, "Wires_PowerBoardToRegulator": {"PowerSwitch", "PowerBoard", "Regulator", "Driver"},
    "Wires_SwitchToPowerBoard": {"PowerSwitch", "PowerBoard"}, "Wires_PowerBoardToNanoVIN": {"PowerSwitch", "PowerBoard", "Arduino_Nano"}, "Wires_RegulatorToServo": {"Regulator", "LevelShifter", "Servo_9g"},
    "Wires_NanoToShifter": {"Arduino_Nano", "LevelShifter"}, "Wires_ServoCable": {"Servo_9g", "LevelShifter"},
    "Wires_DriverToNano": {"Driver", "Arduino_Nano"},
}


def place(shape, pos, axis):
    """Parts are built pointing down -Z from a seat at the origin. Place the seat at pos with the tip along axis."""
    out = shape.copy()
    out.Placement = App.Placement(V(*pos), App.Rotation(V(0, 0, -1), V(*axis)))
    return out


def socket_screw(m, length, pos, axis):
    head_d, head_h, af = SCREW_DIMS[m]
    body = Part.makeCylinder(head_d / 2, head_h, V(0, 0, 0)).fuse(Part.makeCylinder(m / 2.0, length, V(0, 0, -length))).removeSplitter()
    r = af / math.sqrt(3)
    pts = [V(r * math.cos(math.radians(60 * k)), r * math.sin(math.radians(60 * k)), head_h / 2) for k in range(6)]
    recess = Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(0, 0, head_h))
    return place(body.cut(recess), pos, axis)


def heat_insert(spec, m, pos, axis):
    od, tip, length = spec[0], spec[1], spec[2]
    body = Part.makeCone(tip / 2, od / 2, length, V(0, 0, -length)).cut(Part.makeCylinder(m / 2.0, length + 1, V(0, 0, -length - 0.5)))
    return place(body, pos, axis)


def hex_nut(af, height, bore, pos, axis):
    r = af / math.sqrt(3)
    pts = [V(r * math.cos(math.radians(60 * k)), r * math.sin(math.radians(60 * k)), -height) for k in range(6)]
    body = Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(0, 0, height)).cut(Part.makeCylinder(bore, height + 1, V(0, 0, -height - 0.5)))
    return place(body, pos, axis)


DOWN, UP, FORWARD, BACK = (0, 0, -1), (0, 0, 1), (1, 0, 0), (-1, 0, 0)
motor_strap = box(-46.0, -27.4, -8, -2, 21, 22.5).cut(cyl_z(STRAP_SCREW[0], STRAP_SCREW[1], CLEAR_M2, 20, 23))

# (m, length, seat, axis). Every joint is listed here, so the count in the results is the shopping list.
JOINTS_TUB = [(STRAP_SCREW[0], STRAP_SCREW[1], 21.0, 22.5)] + [(x, y, 11.5, 13.1) for x, y in REG_SCREWS]
screws_m2, screws_m3, screws_m16, screws_canopy, screws_tray, nuts = [], [], [], [], [], []
inserts_tub, inserts_knuckle, inserts_canopy = [], [], []
insert_checks = []  # (label, host name, axis, mouth position, spec)
screw_uses = {}


def use(label):
    screw_uses[label] = screw_uses.get(label, 0) + 1


for x, y, face_z, seat_z in JOINTS_TUB:
    screws_m2.append(socket_screw(2, 4, (x, y, seat_z), DOWN))
    use("M2 x 4 socket head")
    inserts_tub.append(heat_insert(INSERT_M2, 2, (x, y, face_z), DOWN))
    insert_checks.append(("tub z=%g" % face_z, "Tub", DOWN, (x, y, face_z), INSERT_M2))
for x, y in TRAY_SCREWS:
    screws_tray.append(socket_screw(2, 4, (x, y, TRAY_Z + 1.5), DOWN))
    use("M2 x 4 socket head")
    inserts_tub.append(heat_insert(INSERT_M2, 2, (x, y, TRAY_Z), DOWN))
    insert_checks.append(("tray post", "Tub", DOWN, (x, y, TRAY_Z), INSERT_M2))
for y in SERVO_SCREWS:
    screws_m2.append(socket_screw(2, 5, (18.5, y, SERVO_HOLE_Z), BACK))
    use("M2 x 5 socket head")
    inserts_tub.append(heat_insert(INSERT_M2, 2, (16, y, SERVO_HOLE_Z), BACK))
    insert_checks.append(("servo tower", "Tub", BACK, (16, y, SERVO_HOLE_Z), INSERT_M2))
NYLOC_M2 = (4.0, 2.8)   # across flats, height (ISO 10511 / DIN 985 M2)
NUT_GAP = 1.3           # pin head clearance ahead of the slot tab: the rod slides 0.9 mm forward at full lock


def washer(od, idia, t, pos, axis):
    ring = Part.makeCylinder(od / 2, t, V(0, 0, -t)).cut(Part.makeCylinder(idia / 2, t + 1, V(0, 0, -t - 0.5)))
    return place(ring, pos, axis)


def spacer(od, idia, length, pos, axis):
    return washer(od, idia, length, pos, axis)


kp_hw, front_hw, tip_hw, horn_hw = {1: [], -1: []}, {1: [], -1: []}, {1: [], -1: []}, []
for s in (1, -1):
    # Kingpin: M2 screw clamps a round spacer and washer down onto the ear insert. The knuckle turns on the spacer.
    kp_top = EAR_TOP + KP_SPACER[2]
    kp_hw[s].append(spacer(KP_SPACER[0], KP_SPACER[1], KP_SPACER[2], (KP_X, s * KINGPIN_Y, kp_top), DOWN))
    kp_hw[s].append(washer(5.0, 2.2, 0.3, (KP_X, s * KINGPIN_Y, kp_top + 0.3), DOWN))
    kp_hw[s].append(socket_screw(2, 16, (KP_X, s * KINGPIN_Y, kp_top + 0.3), DOWN))
    use("M2 x 16 socket head"); use("M2 washer 5 OD x 0.3"); use("Round spacer 4 OD x 2.2 ID x %g (M2)" % KP_SPACER[2])
    inserts_tub.append(heat_insert(INSERT_M2, 2, (KP_X, s * KINGPIN_Y, EAR_TOP), DOWN))
    insert_checks.append(("kingpin ear", "Tub", DOWN, (KP_X, s * KINGPIN_Y, EAR_TOP), INSERT_M2))
    # Front axle: M3 screw clamps a round spacer and washer onto the knuckle insert. The wheel turns on the spacer.
    inward = (0, -s, 0)
    ax_out = KNUCKLE_FACE_Y + AX_SPACER[2]
    front_hw[s].append(spacer(AX_SPACER[0], AX_SPACER[1], AX_SPACER[2], (X_FRONT, s * ax_out, AXLE_Z), inward))
    front_hw[s].append(washer(7.0, 3.2, 0.5, (X_FRONT, s * (ax_out + 0.5), AXLE_Z), inward))
    front_hw[s].append(socket_screw(3, 12, (X_FRONT, s * (ax_out + 0.5), AXLE_Z), inward))
    use("M3 x 12 socket head"); use("M3 washer 7 OD x 0.5"); use("Round spacer 5 OD x 3.2 ID x %g (M3)" % AX_SPACER[2])
    inserts_knuckle.append(heat_insert(INSERT_M3, 3, (X_FRONT, s * KNUCKLE_FACE_Y, AXLE_Z), inward))
    insert_checks.append(("knuckle", "KnuckleL" if s > 0 else "KnuckleR", inward, (X_FRONT, s * KNUCKLE_FACE_Y, AXLE_Z), INSERT_M3))
    # Tie rod to steering arm: M2 x 8 down through rod and arm, nylon lock nut set just free.
    tip_hw[s].append(socket_screw(2, 8, (TX, s * TY, TR_Z[1]), DOWN))
    tip_hw[s].append(hex_nut(NYLOC_M2[0], NYLOC_M2[1], 1.0, (TX, s * TY, ARM_Z[0]), DOWN))
    use("M2 x 8 socket head"); use("M2 nylon lock nut")
    # Canopy: up through the shell ledge into a post on the canopy.
    screws_canopy.append(socket_screw(2, 5, (CANOPY_SCREW[0], s * CANOPY_SCREW[1], CANOPY_LEDGE_TOP - 2), UP))
    use("M2 x 5 socket head")
    inserts_canopy.append(heat_insert(INSERT_M2, 2, (CANOPY_SCREW[0], s * CANOPY_SCREW[1], CANOPY_LEDGE_TOP), UP))
    insert_checks.append(("cabin post", "Cabin", UP, (CANOPY_SCREW[0], s * CANOPY_SCREW[1], CANOPY_LEDGE_TOP), INSERT_M2))
for x, y in NANO_HOLES:
    screws_m16.append(socket_screw(1.6, 4, (x, y, NANO_Z + 1.0), DOWN))
    use("M1.6 x 4 socket head")
# Horn pin: M2 x 10 from the front, through the tie-rod slot, self-tapped into the horn hole drilled 1.6 mm.
# Its head stays NUT_GAP clear of the tab so the rod can slide forward at lock; the horn stops it sliding back.
horn_hw.append(socket_screw(2, 10, (TAB_X1 + NUT_GAP, HORN_AXIS[0], PIN_Z0), BACK))
use("M2 x 10 socket head")
horn_screw = cyl_x(HORN_AXIS[0], HORN_AXIS[1], 2, 31, 32.2)  # head only: this screw comes with the servo
for label in ("683ZZ bearing 3 x 7 x 3", "683ZZ bearing 3 x 7 x 3", "Round spacer 5 OD x 3.2 ID x 4 (rear axle)", "Round spacer 5 OD x 3.2 ID x 4 (rear axle)"):
    use(label)


def horn_at(shape, horn_deg):
    """Turn a part that rides on the servo output by horn_deg (+ pushes the pin toward +Y)."""
    out = shape.copy()
    out.rotate(V(0, HORN_AXIS[0], HORN_AXIS[1]), V(1, 0, 0), -horn_deg)
    return out

def make_bundle(points, r):
    pieces = [Part.makeSphere(r, V(*points[0]))]
    for a, b in zip(points, points[1:]):
        pa, pb = V(*a), V(*b)
        pieces.append(Part.makeCylinder(r, (pb - pa).Length, pa, pb - pa))
        pieces.append(Part.makeSphere(r, pb))
    return Part.makeCompound(pieces)


harness = {name: make_bundle(pts, r) for name, (r, pts) in WIRE_ROUTES.items()}
harness_length = {name: sum((V(*b) - V(*a)).Length for a, b in zip(pts, pts[1:])) for name, (r, pts) in WIRE_ROUTES.items()}

# ---------- Document objects ----------
BODY_PAINT, GLASS, CARBON = (0.90, 0.90, 0.87), (0.03, 0.04, 0.06), (0.09, 0.10, 0.11)
RUBBER, RIM, STEEL = (0.05, 0.05, 0.05), (0.60, 0.62, 0.65), (0.70, 0.72, 0.75)
GREEN, BLUE, BRASS, SILVER, TAN = (0.10, 0.50, 0.28), (0.12, 0.13, 0.15), (0.72, 0.56, 0.25), (0.85, 0.87, 0.90), (0.20, 0.21, 0.23)
HEAD, TAIL_RED = (1.0, 0.97, 0.85), (1.0, 0.10, 0.08)


def add(name, shape, color, group=None):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    if obj.ViewObject:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.DisplayMode = "Shaded"
        obj.ViewObject.Deviation = 0.05
    if group is not None:
        group.addObject(obj)
    return obj


g_div = doc.addObject("App::DocumentObjectGroup", "Divide_RemovableParts")
g_mov = doc.addObject("App::DocumentObjectGroup", "MovingParts")
g_elec = doc.addObject("App::DocumentObjectGroup", "BoughtParts_Placeholder")

printed = {"Shell": add("Shell", shell, BODY_PAINT, g_div), "Nose": add("Nose", nose, BODY_PAINT, g_div),
           "Tail": add("Tail", tail, BODY_PAINT, g_div), "Cabin": add("Cabin", canopy, BODY_PAINT, g_div), "Glass": add("Glass", glass, GLASS, g_div),
           "Wing": add("Wing", wing, BODY_PAINT, g_div), "Splitter": add("Splitter", splitter, CARBON, g_div), "Grille": add("Grille", grille, CARBON, g_div), **{k: add(k, v, CARBON, g_div) for k, v in vent_parts.items()}, "ElectronicsTray": add("ElectronicsTray", tray, TAN, g_div), "MotorStrap": add("MotorStrap", motor_strap, TAN, g_div)}
moving = {}
for name, shape, color in (("TireFL", tire_f, RUBBER), ("RimFL", rim_f, RIM),
                           ("TireFR", mirror_y(tire_f), RUBBER), ("RimFR", mirror_y(rim_f), RIM),
                           ("TireRL", tire_r, RUBBER), ("RimRL", rim_r_, RIM),
                           ("TireRR", mirror_y(tire_r), RUBBER), ("RimRR", mirror_y(rim_r_), RIM),
                           ("KnuckleL", knuckle, TAN), ("KnuckleR", mirror_y(knuckle), TAN),
                           ("AxleSpacerL", rear_spacer, STEEL), ("AxleSpacerR", mirror_y(rear_spacer), STEEL),
                           ("TieRod", tie_rod, STEEL), ("RearAxle", axle, STEEL), ("AxleGear", gear, BRASS),
                           ("Pinion", pinion, BRASS), ("BearingL", bearing, STEEL), ("BearingR", mirror_y(bearing), STEEL),
                           ("ServoHorn", horn, SILVER)):
    moving[name] = add(name, shape, color, g_mov)
bought = {}
for name, shape, color in (("Motor_N20", motor, STEEL), ("Battery_2S", battery, BLUE), ("Arduino_Nano", nano, GREEN), ("LevelShifter", level_shifter, GREEN),
                           ("Regulator", regulator, GREEN), ("PowerSwitch", power_switch, SILVER), ("PowerBoard", power_board, GREEN),
                           ("Servo_9g", servo, BLUE), ("Driver", driver, GREEN), ("Magnets", magnets, SILVER),
                           ("HeadBezels", head_bezels, CARBON), ("FogLights", fog_lights, (1.0, 0.82, 0.10)), ("HeadLights", head_lights, HEAD), ("TailLights", tail_lights, TAIL_RED)):
    bought[name] = add(name, shape, color, g_elec)
g_wire = doc.addObject("App::DocumentObjectGroup", "Wiring")
WIRE_COLOR = {"Wires_MotorToDriver": (0.95, 0.75, 0.10), "Wires_BatteryToSwitch": (0.90, 0.10, 0.10), "Wires_PowerBoardToDriver": (0.90, 0.10, 0.10),
              "Wires_PowerBoardToRegulator": (0.90, 0.10, 0.10), "Wires_PowerBoardToNanoVIN": (0.90, 0.10, 0.10), "Wires_SwitchToPowerBoard": (0.3, 0.3, 0.9), "Wires_RegulatorToServo": (0.95, 0.45, 0.05),
              "Wires_NanoToShifter": (0.60, 0.35, 0.85), "Wires_ServoCable": (0.95, 0.55, 0.20), "Wires_DriverToNano": (0.15, 0.75, 0.85)}
for name, shape in harness.items():
    add(name, shape, WIRE_COLOR[name], g_wire)
g_fast = doc.addObject("App::DocumentObjectGroup", "Fasteners")
SCREW_COLOR, BRASS_INSERT, NUT_COLOR = (0.16, 0.16, 0.18), (0.85, 0.65, 0.20), (0.75, 0.76, 0.78)
hardware = {}
for name, shape, color in (("Screws_M2", Part.makeCompound(screws_m2), SCREW_COLOR),
                           ("Screws_M1p6_Nano", Part.makeCompound(screws_m16), SCREW_COLOR), ("Screws_Cabin", Part.makeCompound(screws_canopy), SCREW_COLOR),
                           ("Screws_Tray", Part.makeCompound(screws_tray), SCREW_COLOR),
                           ("Kingpin_L", Part.makeCompound(kp_hw[1]), SCREW_COLOR), ("Kingpin_R", Part.makeCompound(kp_hw[-1]), SCREW_COLOR),
                           ("FrontAxleHW_L", Part.makeCompound(front_hw[1]), SCREW_COLOR), ("FrontAxleHW_R", Part.makeCompound(front_hw[-1]), SCREW_COLOR),
                           ("TieRodJoint_L", Part.makeCompound(tip_hw[1]), NUT_COLOR), ("TieRodJoint_R", Part.makeCompound(tip_hw[-1]), NUT_COLOR),
                           ("HornPin", Part.makeCompound(horn_hw), SCREW_COLOR),
                           ("Inserts_Tub", Part.makeCompound(inserts_tub), BRASS_INSERT), ("Inserts_Knuckles", Part.makeCompound(inserts_knuckle), BRASS_INSERT),
                           ("Inserts_Cabin", Part.makeCompound(inserts_canopy), BRASS_INSERT), ("ServoHornScrew", horn_screw, SCREW_COLOR)):
    hardware[name] = add(name, shape, color, g_fast)
doc.recompute()

# ---------- Checks: every number below is measured from the solids ----------
results = {"checks": {}, "notes": notes, "parts": {}}
everything = {"Tub": tub.Shape}
for group in (printed, moving, bought, hardware):
    for name, obj in group.items():
        everything[name] = obj.Shape


def record(name, value, limit, ok):
    results["checks"][name] = {"value": value, "limit": limit, "pass": bool(ok)}


def overlap(a, b):
    """Test solid by solid: a boolean on a compound of overlapping solids can silently miss a clash."""
    if not a.BoundBox.intersect(b.BoundBox):
        return 0.0
    total = 0.0
    for sa in (a.Solids or [a]):
        for sb in (b.Solids or [b]):
            if sa.BoundBox.intersect(sb.BoundBox):
                try:
                    total += sa.common(sb).Volume
                except Exception:
                    return float("nan")
    return total


full = Part.makeCompound(list(everything.values())).BoundBox
size = (round(full.XLength, 2), round(full.YLength, 2), round(full.ZLength, 2))
record("car_size_straight_mm", size, ENVELOPE, all(a <= b for a, b in zip(size, ENVELOPE)))

# How closely the body follows the traced centreline. Reported, the wheels and tub limit how exact it can be.
trace_fit = {}
for px, py in TRACE:
    x, z = trace_x(px), trace_z(py)
    if x > FACE_X - 0.5:
        x = FACE_X - 0.5
    line = Part.makeLine(V(x, 0, 0), V(x, 0, 90))
    tops = [e.BoundBox.ZMax for shape in (master, canopy_outer) for e in line.common(shape).Edges]
    trace_fit["x=%.0f" % x] = round(max(tops) - z, 1) if tops else None
results["trace_error_mm"] = trace_fit


fits, solid_ok = {}, {}
for name, shape in (("Tub", tub.Shape), ("Shell", shell), ("Nose", nose), ("Tail", tail), ("Cabin", canopy), ("Glass", glass), ("Wing", wing), ("Splitter", splitter), ("Grille", grille), ("ElectronicsTray", tray), ("MotorStrap", motor_strap)):
    bb = shape.BoundBox
    dims = sorted((bb.XLength, bb.YLength, bb.ZLength), reverse=True)
    results["parts"][name] = {"bbox_mm": [round(bb.XLength, 1), round(bb.YLength, 1), round(bb.ZLength, 1)],
                              "volume_cm3": round(mesh_volume(shape) / 1000, 1), "solids": len(shape.Solids),
                              "valid": shape.isValid()}
    fits[name] = all(d <= p for d, p in zip(dims, PRINTER))
    solid_ok[name] = (len(shape.Solids), shape.isValid() and mesh_volume(shape) > 0)  # a failed boolean can report valid with negative volume
record("each_printed_part_fits_printer", fits, PRINTER, all(fits.values()))
record("printed_parts_single_valid_solid", solid_ok, "1 solid, valid, positive volume", all(v == (1, True) for v in solid_ok.values()))

# A bad boolean can report a valid shape, so measure the cut two independent ways.
record("shell_left_inside_cockpit_mm3", round(canopy_leftover, 3), "<= 0.01", canopy_leftover <= 0.01)
cut_error = abs(canopy_cut_actual - canopy_cut_expected) / canopy_cut_expected * 100
record("canopy_cut_volume_error_pct", round(cut_error, 2), "<= 1", cut_error <= 1)
results["canopy_cut_mm3"] = {"actual": round(canopy_cut_actual, 1), "expected": round(canopy_cut_expected, 1)}

# Meant to overlap: an insert melts into a slightly smaller hole, and the M1.6 screws cut their own thread.
INTENDED = {frozenset(p) for p in (("Inserts_Tub", "Tub"), ("Inserts_Knuckles", "KnuckleL"), ("Inserts_Knuckles", "KnuckleR"),
                                   ("Inserts_Cabin", "Cabin"), ("Screws_M1p6_Nano", "ElectronicsTray"),
                                   ("TireFL", "RimFL"), ("TireFR", "RimFR"), ("TireRL", "RimRL"), ("TireRR", "RimRR"),  # tyres stretch over the rims
                                   ("HornPin", "ServoHorn"))}  # the pin self-taps into the horn
clashes = {}
names = list(everything)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        if frozenset((a, b)) in INTENDED:
            continue
        vol = overlap(everything[a], everything[b])
        if vol != vol or vol > 0.01:
            clashes["%s/%s" % (a, b)] = round(vol, 3)
record("static_interference_mm3", clashes, "none above 0.01", not clashes)

# Steering: solve the real linkage (inner and outer wheels differ) and move every part that steers, at a third,
# two thirds and full lock each way. Nothing may touch, and the horn pin must stay inside its slot.
STEER_MOVING = {"TireFL", "RimFL", "TireFR", "RimFR", "KnuckleL", "KnuckleR", "TieRod", "ServoHorn", "HornPin", "TieRodJoint_L",
                "TieRodJoint_R", "FrontAxleHW_L", "FrontAxleHW_R", "Inserts_Knuckles"}
steer_static = {k: v for k, v in everything.items() if k not in STEER_MOVING}
steer_static.update(harness)
steer_clash, slot_report = {}, {}
min_gap, widest_lock = 1e9, 0.0
for turn in (1, -1):
    for frac in (1 / 3.0, 2 / 3.0, 1.0):
        inner = STEER_DEG * frac
        l, r, dy, dx, yaw, horn_deg = steer_pose(inner, turn)
        tag = "%s %.0f%%" % ("left" if turn > 0 else "right", frac * 100)
        groups = {}
        for s, ang in ((1, l), (-1, r)):
            k = "L" if s > 0 else "R"
            w = wheel_f if s > 0 else mirror_y(wheel_f)
            kn = knuckle if s > 0 else mirror_y(knuckle)
            groups["wheel" + k] = steered(w, ang, s)
            groups["knuckle" + k] = steered(kn, ang, s)
            groups["axleHW" + k] = steered(Part.makeCompound(front_hw[s]), ang, s)
            groups["tipjoint" + k] = rod_at(Part.makeCompound(tip_hw[s]), inner, turn)
            bb = groups["wheel" + k].BoundBox
            widest_lock = max(widest_lock, 2 * max(abs(bb.YMin), abs(bb.YMax)),
                              2 * max(abs(groups["axleHW" + k].BoundBox.YMin), abs(groups["axleHW" + k].BoundBox.YMax)))
        groups["tierod"] = rod_at(tie_rod, inner, turn)
        groups["horn"] = horn_at(horn, horn_deg)
        groups["hornpin"] = horn_at(Part.makeCompound(horn_hw), horn_deg)
        for gname, gshape in groups.items():
            for sname, sshape in steer_static.items():
                vol = overlap(gshape, sshape)
                if vol != vol or vol > 0.01:
                    steer_clash["%s %s vs %s" % (tag, gname, sname)] = round(vol, 3)
        gl = list(groups)
        for i, a in enumerate(gl):
            for b in gl[i + 1:]:
                pair = {a, b}
                if pair in ({"tierod", "hornpin"}, {"horn", "hornpin"}) or (a[:-1], b[:-1]) in (("knuckle", "tipjoint"), ("tipjoint", "knuckle")) and a[-1] == b[-1]:
                    continue  # pins through their own holes, checked by the slot test and the hole sizes
                vol = overlap(groups[a], groups[b])
                if vol != vol or vol > 0.01:
                    steer_clash["%s %s vs %s" % (tag, a, b)] = round(vol, 3)
        for k in ("L", "R"):
            min_gap = min(min_gap, groups["wheel" + k].distToShape(tub.Shape)[0], groups["wheel" + k].distToShape(shell)[0],
                          groups["wheel" + k].distToShape(nose)[0], groups["wheel" + k].distToShape(splitter)[0])
        # Horn pin in the slot, in the rod's own frame.
        pin = horn_at(Part.Vertex(V(SLOT_X, HORN_AXIS[0], PIN_Z0)), horn_deg).Point
        local = V(pin.x - dx, pin.y - dy, pin.z)
        a = -math.radians(yaw)
        ly = (local.x - TX) * math.sin(a) + local.y * math.cos(a)
        slot_report[tag] = {"left_deg": round(l, 1), "right_deg": round(r, 1), "horn_deg": round(horn_deg, 1),
                            "pin_z": round(pin.z, 2), "pin_y_in_slot": round(ly, 3), "rod_dx": round(dx, 2), "rod_yaw_deg": round(yaw, 2)}
pin_ok = all(SLOT_Z[0] + 1.0 <= v["pin_z"] <= SLOT_Z[1] - 1.0 and abs(v["pin_y_in_slot"]) <= SLOT_HALF_W - 1.0 + 1e-3
             and -0.25 <= v["rod_dx"] <= NUT_GAP - 0.2 for v in slot_report.values())
results["steering"] = {"inner_lock_deg": STEER_DEG, "outer_lock_deg": round(OUTER_DEG, 2), "kingpin_trail_mm": KP_TRAIL,
                       "arm_tip": [round(ARM_TIP[0], 2), round(ARM_TIP[1], 2)], "poses": slot_report,
                       "horn_deg_at_full_lock": round(max(abs(v["horn_deg"]) for v in slot_report.values()), 1)}
record("steering_sweep_clash_mm3", steer_clash, "none, real linkage, 1/3 to full lock both ways", not steer_clash)
record("horn_pin_stays_in_slot", pin_ok, "pin inside slot height and width, rod slide within nut gap", pin_ok)
record("car_width_at_steering_lock_mm", round(widest_lock, 2), ENVELOPE[1], widest_lock <= ENVELOPE[1])
record("front_wheel_min_gap_at_lock_mm", round(min_gap, 2), ">= 0.5", min_gap >= 0.5)

# Each removable part must come off along its own direction without hitting what stays on the car.
stays = {k: v for k, v in everything.items() if k not in ("Shell", "Cabin", "Glass", "Magnets", "Nose", "Tail", "Wing", "Splitter", "Grille", "VentHoodL", "VentHoodR", "VentSideL", "VentSideR", "HeadBezels", "FogLights", "HeadLights", "TailLights", "Screws_Cabin", "Inserts_Cabin")}
stays.update(harness)
removal = {}
for pname, shape, step in (("Shell", shell, (0, 0, 1)), ("Cabin", canopy, (0, 0, 1)), ("Splitter", splitter, (0, 0, -1)), ("Nose", nose, (1, 0, 0)), ("Tail", tail, (-1, 0, 0)), ("Wing", wing, (0, 0, 1))):
    for dist in (1, 3, 6, 12, 25, 45):
        lifted = moved(shape, step[0] * dist, step[1] * dist, step[2] * dist)
        for sname, sshape in stays.items():
            vol = overlap(lifted, sshape)
            if vol != vol or vol > 0.01:
                removal["%s at %g mm vs %s" % (pname, dist, sname)] = round(vol, 3)
record("removable_parts_come_off_clear", removal, "no contact", not removal)

# Wiring: nothing may pass through a solid, at straight-ahead or with the steering at either lock.
def wire_clashes(bundles, ignore_ends=False):
    found = {}
    for wname, wshape in bundles.items():
        for oname, oshape in everything.items():
            if ignore_ends and oname in WIRE_ENDS[wname]:
                continue
            vol = overlap(wshape, oshape)
            if vol != vol or vol > 0.05:
                found["%s/%s" % (wname, oname)] = round(vol, 2)
        for turn in (1, -1):
            rod = rod_at(tie_rod, STEER_DEG, turn)
            vol = overlap(wshape, rod)
            if vol != vol or vol > 0.05:
                found["%s/tie rod %s lock" % (wname, "left" if turn > 0 else "right")] = round(vol, 2)
    return found


wire_found = wire_clashes(harness)
record("wiring_clash_mm3", wire_found, "none above 0.05", not wire_found)
results["wire_lengths_mm"] = {k: round(v) for k, v in harness_length.items()}

# Room to spare: repeat with every bundle fatter. Reported, not a pass/fail limit.
margin = {}
for extra in (0.5, 1.0, 1.5):
    fat = {name: make_bundle(pts, r + extra) for name, (r, pts) in WIRE_ROUTES.items()}
    margin["+%.1f mm radius" % extra] = wire_clashes(fat, ignore_ends=True)
results["wiring_margin"] = margin

# Service: battery must lift straight out with the shell and tray off. Wires are flexible and move aside.
rigid = {k: v for k, v in everything.items() if k not in ("Shell", "Cabin", "Glass", "Magnets", "Nose", "Tail", "Wing", "Splitter", "Grille", "VentHoodL", "VentHoodR", "VentSideL", "VentSideR", "HeadBezels", "FogLights", "HeadLights", "TailLights", "ElectronicsTray", "Arduino_Nano", "Battery_2S",
                                                          "Screws_Tray", "Screws_M1p6_Nano", "Screws_Cabin", "Inserts_Cabin")}
battery_clash = {}
for dist in (1, 3, 6, 12, 25, 45):
    lifted = moved(battery, dz=dist)
    for sname, sshape in rigid.items():
        vol = overlap(lifted, sshape)
        if vol != vol or vol > 0.01:
            battery_clash["at %g mm vs %s" % (dist, sname)] = round(vol, 3)
record("battery_lifts_out_with_tray_off", battery_clash, "no contact", not battery_clash)
# Install path: a model can fit parts it could never get them into. The motor must drop in clear of the tub.
motor_clash = {}
for dist in (1, 3, 6, 12, 25):
    vol = overlap(moved(motor, dz=dist), tub.Shape)
    if vol != vol or vol > 0.01:
        motor_clash["at %g mm" % dist] = round(vol, 3)
record("motor_drops_into_cradle", motor_clash, "no contact", not motor_clash)
results["headroom_mm"] = {"nano_to_cabin": round(nano.distToShape(canopy)[0], 2), "regulator_to_shell": round(regulator.distToShape(shell)[0], 2),
                          "driver_to_shell": round(driver.distToShape(shell)[0], 2)}

# Heat-set inserts: every hole needs the vendor's minimum wall of plastic all the way round.
hosts = {"Tub": tub.Shape, "KnuckleL": knuckle, "KnuckleR": mirror_y(knuckle), "Cabin": canopy}
thin = {}
for label, host, axis, mouth, spec in insert_checks:
    hole_r, wall = spec[3] / 2, spec[4]
    ring = Part.makeCylinder(hole_r + wall, spec[2], V(0, 0, -spec[2])).cut(Part.makeCylinder(hole_r, spec[2] + 1, V(0, 0, -spec[2] - 0.5)))
    missing = place(ring, mouth, axis).cut(hosts[host]).Volume
    if missing > 0.2:
        thin["%s at %s" % (label, tuple(round(v, 1) for v in mouth))] = round(missing, 2)
record("insert_wall_missing_mm3", thin, "<= 0.2 inside the vendor minimum wall", not thin)

# Thread engagement: measure how far a screw actually reaches into each insert's threaded bore.
all_screws = Part.makeCompound(screws_m2 + screws_canopy + screws_tray + kp_hw[1] + kp_hw[-1] + front_hw[1] + front_hw[-1])
engagement = {}
for label, host, axis, mouth, spec in insert_checks:
    m = 2.0 if spec is INSERT_M2 else 3.0
    area = math.pi * (m / 2) ** 2
    bore = place(Part.makeCylinder(m / 2, spec[2], V(0, 0, -spec[2])), mouth, axis)
    engaged = sum(bore.common(s).Volume for s in all_screws.Solids if bore.BoundBox.intersect(s.BoundBox)) / area
    engagement["%s at %s" % (label, tuple(round(v, 1) for v in mouth))] = round(engaged, 2)
record("thread_engagement_mm", engagement, ">= 2.0", all(v >= 2.0 - 0.01 for v in engagement.values()))
results["hardware_counts"] = screw_uses
results["hardware_counts"]["M2 x 3 heat insert"] = sum(1 for c in insert_checks if c[4] is INSERT_M2)
results["hardware_counts"]["M3 x 3 short heat insert"] = sum(1 for c in insert_checks if c[4] is INSERT_M3)

# Weight, tipping and drive. Printed parts are counted solid, which is the heavy, cautious case for thin walls.
def mesh_props(shape):
    pts, tris = shape.tessellate(0.1)
    six_v, moment = 0.0, V(0, 0, 0)
    for a, b, c in tris:
        v = pts[a].dot(pts[b].cross(pts[c]))
        six_v += v
        moment = moment + (pts[a] + pts[b] + pts[c]) * (v / 4.0)
    return six_v / 6.0, moment * (1.0 / six_v)


PLA, TPU = 1.24e-3, 1.21e-3  # g/mm3
LISTED_G = {"Motor_N20": 9.5, "Servo_9g": 9.0, "Battery_2S": 18.0, "Driver": 1.0}
ESTIMATED_G = {"Arduino_Nano": 5.0, "Regulator": 2.0, "LevelShifter": 0.5, "PowerSwitch": 1.0, "PowerBoard": 0.6, "RearAxle": 1.7, "AxleGear": 3.0, "Pinion": 1.0,
               "BearingL": 0.5, "BearingR": 0.5, "Magnets": 8.5, "Screws_M2": 3.0, "FrontAxleHW_L": 1.5, "FrontAxleHW_R": 1.5, "Kingpin_L": 0.6, "Kingpin_R": 0.6, "HornPin": 0.6, "AxleSpacerL": 0.2, "AxleSpacerR": 0.2}
mass_items = []
for name in list(printed) + ["Tub", "RimFL", "RimFR", "RimRL", "RimRR"]:
    volume, centre = mesh_props(everything[name])
    mass_items.append((volume * PLA, centre))
for name in ("TireFL", "TireFR", "TireRL", "TireRR"):
    volume, centre = mesh_props(everything[name])
    mass_items.append((volume * TPU, centre))
for name, grams in list(LISTED_G.items()) + list(ESTIMATED_G.items()):
    mass_items.append((grams, everything[name].BoundBox.Center))
total_g = sum(m for m, c in mass_items)
cg = V(0, 0, 0)
for m, c in mass_items:
    cg = cg + c * m
cg = cg * (1.0 / total_g)
results["mass"] = {"total_g": round(total_g, 1), "cg_mm": [round(cg.x, 1), round(cg.y, 2), round(cg.z, 1)],
                   "front_axle_load_pct": round((cg.x - X_REAR) / (X_FRONT - X_REAR) * 100, 1)}
# Motor: Pololu #3061, 10:1 HPCB 6V: 3300 rpm no load, 0.17 kg.cm stall (theoretical). 2:1 gears to the axle.
# Same 10 x 12 x 25 mm body and 3 mm D shaft as the other ratios, so the model does not change.
GEAR_RATIO, MOTOR_RPM, MOTOR_STALL_KGCM = 2.0, 3300.0, 0.17
SLOW_VOLTS = 70 / 255.0 * 8.4   # slow mode on a full battery, as motor voltage
top_speed = MOTOR_RPM / GEAR_RATIO * 2 * math.pi * (WHEEL_R / 1000) / 60
wheelbase_m = (X_FRONT - X_REAR) / 1000
half_track = (FRONT_IN + FRONT_OUT) / 2
tip_g = half_track / cg.z


def turn_g_at(speed, lock_deg):
    return speed ** 2 / (wheelbase_m / math.tan(math.radians(lock_deg))) / 9.81


# User decision: tipping is allowed, it is part of the fun. Reported only, with full steering at any speed.
turn_g = turn_g_at(top_speed, STEER_DEG)
slow_speed = top_speed * SLOW_VOLTS / 6.0
slow_turn_g = turn_g_at(slow_speed, STEER_DEG)
results["tipping"] = {"tip_margin_at_top_speed_full_lock": round(tip_g / turn_g, 2), "tip_margin_slow_mode_full_lock": round(tip_g / slow_turn_g, 2),
                      "tip_speed_full_lock_m_s": round(math.sqrt(tip_g * 9.81 * wheelbase_m / math.tan(math.radians(STEER_DEG))), 2),
                      "tire_grip_needed_to_tip": round(tip_g, 2)}
weight_n = total_g / 1000 * 9.81
drive_force = MOTOR_STALL_KGCM * GEAR_RATIO * 9.81 / 100 / (WHEEL_R / 1000)
# Sizing rule: run a brushed motor at no more than 1/4 of stall. Indoors on flat floors (user), so the load is rolling drag, assumed 5% of weight.
needed = weight_n * 0.05
record("drive_force_margin", round(drive_force / 4 / needed, 2), ">= 1 (quarter stall force / rolling drag on a flat floor)", drive_force / 4 >= needed)
results["drive"] = {"top_speed_no_load_m_s": round(top_speed, 2), "slow_mode_m_s": round(slow_speed, 2), "time_constant_s": round(total_g / 1000 * top_speed / drive_force, 2), "stall_force_n": round(drive_force, 2), "needed_force_n": round(needed, 2),
                    "tip_g": round(tip_g, 2), "turn_g": round(turn_g, 3)}

for nm, wheel_shape in (("rear_wheel_gap_to_tub_mm", tire_r.fuse(rim_r_)),):
    gap = wheel_shape.distToShape(tub.Shape)[0]
    record(nm, round(gap, 2), ">= 2", gap >= 2 - 1e-6)
gap = tire_r.distToShape(shell)[0]
record("rear_wheel_gap_to_shell_mm", round(gap, 2), ">= 1", gap >= 1)
results["ground_clearance_mm"] = {"tub": round(tub.Shape.BoundBox.ZMin, 2), "splitter": round(splitter.BoundBox.ZMin, 2)}
results["all_pass"] = all(c["pass"] for c in results["checks"].values())

# ---------- Print files ----------
import Mesh, MeshPart
stl_dir = os.path.join(OUT_DIR, "stl")
os.makedirs(stl_dir, exist_ok=True)
fit = box(0, 58, 0, 26, 0, 9)
fit = fit.cut(cyl_z(6, 6, INSERT_M2[3] / 2, 9 - INSERT_HOLE_DEPTH, 10))       # M2 insert
fit = fit.cut(cyl_z(16, 6, INSERT_M3[3] / 2, 9 - INSERT_HOLE_DEPTH, 10))      # M3 insert
fit = fit.cut(cyl_z(27, 6, MAG_R + MAG_CLEAR, 9 - pocket_depth, 10))          # magnet
fit = fit.cut(cyl_z(39, 6, BEARING_R + 0.05, 9 - BEARING_T, 10)).cut(cyl_z(39, 6, 2.0, -1, 10))  # bearing and axle clearance
fit = fit.cut(cyl_z(50, 6, CLEAR_M2, -1, 10))                                 # M2 clearance
fit = fit.cut(cyl_z(50, 18, 0.65, 4, 10))                                     # M1.6 pilot
fit = fit.cut(cyl_z(40, 18, 1.7, 7, 10))                                      # locating pin hole
fit = fit.fuse(cyl_z(30, 18, 1.5, 9, 10.8))                                   # locating pin
fit = fit.cut(box(2, 14.1, 13, 26.5, 9 - 3.5, 10))                            # motor cradle width: 12 mm motor slides in from the edge
# v2 fits: knuckle on its 4 mm spacer, front wheel on its 5 mm spacer, rear wheel D bore on the 3 mm D shaft.
fit = fit.cut(cyl_z(19, 19, KP_SPACER[0] / 2 + 0.1, -1, 10))
fit = fit.cut(cyl_z(55, 19, AX_SPACER[0] / 2 + 0.1, -1, 10))
d_hole = d_profile_y(0, 0, D_SHAFT[0], D_SHAFT[1], -1, 11)
d_hole.rotate(V(0, 0, 0), V(1, 0, 0), 90)
fit = fit.cut(moved(d_hole, 46, 22, 0))
stl_report = {}
to_export = {name: everything[name] for name in printed}
to_export["Tub"] = everything["Tub"]
for name in ("KnuckleL", "KnuckleR", "TieRod", "RimFL", "RimFR", "RimRL", "RimRR", "TireFL", "TireFR", "TireRL", "TireRR"):
    to_export[name] = everything[name]
to_export["FitTest_print_this_first"] = fit
to_export["ALT_Pinion_12T_m0.6_printed"] = alt_pinion
to_export["ALT_AxleGear_17T_m0.6_printed"] = alt_gear
for name, shape in to_export.items():
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.03, AngularDeflection=0.2, Relative=False)
    mesh.write(os.path.join(stl_dir, name + ".stl"))
    stl_report[name] = {"watertight": bool(mesh.isSolid()) and not mesh.hasNonManifolds(), "volume_cm3": round(mesh.Volume / 1000, 2), "triangles": mesh.CountFacets}
results["stl"] = stl_report
record("stl_files_watertight", [k for k, v in stl_report.items() if not v["watertight"]], "none leaking", all(v["watertight"] for v in stl_report.values()))
results["all_pass"] = all(c["pass"] for c in results["checks"].values())

# Show only finished parts when the file is opened: hide sketches and intermediate Part Design features.
for o in doc.Objects:
    if o.TypeId.startswith("Sketcher::") or (o in tub.Group and o is not tub.Tip):
        o.Visibility = False
# One STEP of the whole assembled car, for any CAD program (Fusion, Onshape, SolidWorks, FreeCAD).
import Import
step_objs = [tub] + [o for o in doc.Objects if o.TypeId == "Part::Feature"]
Import.export(step_objs, os.path.join(OUT_DIR, "RC_Car_assembly.step"))
doc.saveAs(os.path.join(OUT_DIR, "RC_Car.FCStd"))
with open(os.path.join(OUT_DIR, "rc_car_results.json"), "w") as fh:
    json.dump(results, fh, indent=2, default=str)

if Gui and getattr(Gui, "ActiveDocument", None) is not None:
    if tub.ViewObject:  # only the tip feature should show, otherwise the body renders empty
        for feature in tub.Group:
            if feature.ViewObject:
                feature.ViewObject.Visibility = feature is tub.Tip
        tub.ViewObject.Visibility = True
        tub.ViewObject.ShapeColor = CARBON
        tub.ViewObject.DisplayMode = "Shaded" if "Shaded" in tub.ViewObject.getEnumerationsOfProperty("DisplayMode") else tub.ViewObject.DisplayMode
    view = Gui.ActiveDocument.ActiveView if Gui.ActiveDocument else None
    if view:
        view.viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")

print(json.dumps(results, indent=1, default=str))
