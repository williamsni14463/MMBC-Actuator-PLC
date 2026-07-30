# Setting Up the Tolomatic IMA44 Actuator with a Kollmorgen AKD2G Drive

---

## 1. The parts

| Part | Model | What it does |
|---|---|---|
| Actuator | Tolomatic **IMA444RN04SK6MV43DX12A4N** | Motor + 4 mm-lead roller screw. `MV43` = 460 V winding. No brake. |
| Drive | Kollmorgen **AKD2G-SPE-7V06S-A1F3-0000** | 480 V, 3-phase, 6 A, single axis, STO safety, EtherCAT. |
| Cable | Kollmorgen hybrid **H6-21-015-B1-VL-012000** | Carries motor power **and** feedback in one cable. |
| Regen resistor | 33 Ω / 1.5 kW (BAR-1500-33) | Burns off braking energy so the drive doesn't over-volt. |
| 24 V supply | any isolated 24 VDC PELV | Powers the drive's logic and the safety inputs. |
| Software | Kollmorgen **WorkBench** | Where you configure and test the drive. |

---

## 2. How it all connects

| Drive connector | What lands there |
|---|---|
| **X3** | Mains 480 V 3-phase (PE, L1, L2, L3) with the regen resistor in RE and DC+ |
| **X1** | The hybrid cable — motor power **and** feedback, in one plug |
| **X10** | 24 V logic supply (pin 1 = +24 V, pin 2 = GND) |
| **X20** | Service Ethernet — plug your laptop here for WorkBench |
| **X21** | Safety + enable signals (see below) |

**The regen resistor (on X3):** connect it across **+DC (+RBext)** and **Re (RBext−)**.

**The enable signals (on X21)** — the drive needs all of these before it will make torque:

| Signal | Pin | Needs |
|---|---|---|
| STO channel A | **A11** | +24 V |
| STO channel B | **B11** | +24 V |
| Hardware Enable (Axis 1) | **A5** | +24 V |
| +24 V source | **B3** | from your PSU + |
| Ground | **B4** | from your PSU − |

**STO (Safe Torque Off)** is a safety function. Both channels
must see 24 V for the motor to be allowed to move; drop either one and the drive
instantly cuts motor power. Two independent channels means one can fail and the safety
still works. 

For the bench test, I just jumped A11, B11, B3, and A5 on the same cable. But for operation, they should get different power supplies for safety reasons.

---

## 3. Setting it up in WorkBench 

Connect your laptop to **X20**, open WorkBench, **New Project → Add New Device →
Online – Ethernet**, pick the drive, connect./

Then do the following screens **in this order**. Order matters: the drive can't align
the motor (Step 7) until it knows the motor (Step 5), and can't be tuned (Step 9) until
it's aligned.

---

## 5. Motor parameters (the numbers)

Go to **Axis 1 → Motor**. Set **Motor Autoset = 0 (Off)** — this unlocks the fields so
you can type. (Autoset only auto-fills for genuine Kollmorgen motors; yours is a
Tolomatic, so you enter them by hand.)

Enter these **exact MV43 values** (confirmed by FPE Automation in WorkBench units):

| Field | Value | Unit |
|---|---|---|
| Continuous Current | **5** | Arms |
| Peak Current | **15** | Arms |
| Coil Thermal Constant | **1.768388** | mHz |
| Inductance (quad) | **11.5** | mH |
| Inductance (direct) | **11.5** | mH |
| Inductance Saturation | *(leave default)* | Arms |
| Motor Poles | **8** | — |
| Inertia | **9.60209** | kg·cm² |
| Torque Constant | **1.693717** | Nm/Arms |
| EMF Constant | **108.2580** | Vrms/kRPM |
| Motor Resistance | **2.32** | Ohm |
| Maximum Voltage | **460** | Vrms |
| Maximum Speed | **3500** | rpm |

Then click **Create Motor** to save it as a custom motor.

> **A useful sanity check.** For a healthy motor, EMF Constant ÷ Torque Constant ≈ 60.
> Here: 108.258 ÷ 1.693717 = **63.9**. ✓ If you ever get a number near 127, your Kt/Ke
> are in the wrong units (peak instead of RMS) — that mis-scales the current and causes
> overload faults.

---

## 6. The other setup screens

**Power** (Device Settings → Power): Input Mains = **AC**, Nominal AC Line ≈ **480 Vrms**,
AC Line Phases = **3-phase**. *(This is your 7V/480 V drive — don't copy single-phase examples.)*

**Motor Temperature** (Axis 1 → Motor → Motor Temperature): **127 – No Thermal Sensor.**
*(Your actuator's sensor isn't wired to the drive, so this stops a false over-temp fault.)*

**Feedback 1** (Device Settings → Feedback Devices → Feedback 1): disable the drive first.
Look at the **"Feedback Identified"** field — it shows what the drive actually detects.
Set **Feedback Selection** to match it (**46 – HIPERFACE DSL**, or **45 – SFD3**). Set
Mechanic Type = **0 – Rotary**.

**Brake** (Axis 1 → Brake): Usage = **0 – Not Used.** *(Your actuator has no brake.)*

---

## 7. Commutation alignment (Wake & Shake) — the step that trips people

**What it is:** the drive needs to know how the feedback's "zero" lines up with the
motor's magnetic poles, so it energizes the coils at the right angle. That alignment
number is the **commutation offset** (shown as *Motor Phase*). Get it wrong and the
motor pushes against itself — you get a loud buzz and a **motor overload fault**.

Go to **Axis 1 → Motor → Wake and Shake**:
1. Set Method = **2 – Auto Wake and Shake.** ← always use this one.
2. Click **ARM.**
3. **Enable** the drive. It runs the alignment (~1 minute).
4. Confirm it says **Successful** and Motor Phase is around **~100°**.
5. Run it a second time — a good result repeats to about the same number.

> **⚠️ The mistake that cost us a day:** switching to the *old* (non-Auto) Wake & Shake.
> It landed a full phase off (**239°** instead of ~100°), and the next jog command threw
> a motor overload and broke tuning. **Only use Method 2 (Auto).** If you ever see ~120°
> or ~240° instead of ~100°, re-run Auto Wake & Shake — don't try to move it.

---

## 8. Units and Home

**Units** (Axis 1 → Units): Type of Mechanics = **Lead Screw**, Lead = **4 mm**
(your `RN04` screw — *not* 5 mm), Motor = 1, Load = 1. *(This tells the drive how motor
turns convert to millimeters of rod travel.)*

**Home** (Axis 1 → Home): jog the rod to where you want "zero," then set
**0 – Current position** and Start. Position feedback should read 0.000 mm.

---

## 9. Testing it with Jog Motion

Now the fun part. Go to **Axis 1 → Motion → Jog Motion.**

1. Set **low** values first: Velocity ~100 rpm, Acceleration/Deceleration modest.
2. **Enable** the drive (toolbar).
3. Press and hold the **◄ / ►** arrows to extend and retract the rod.
4. Watch **Position Feedback** change smoothly as it moves.

**Start slow, every time.** Keep the velocity low, keep your hand near the E-stop, and
keep the rod away from both physical end stops until you trust the motion. The roller
screw back-drives and there's no brake, so the rod won't hold position when the drive
is disabled.

**Autotune:** with motion confirmed, run **Axis 1 → Performance Servo Tuner** (Excitation
= Automatic, Mode = Autotune, Start). It measures your real load and sets good control
gains. The motor will jiggle on purpose during this — that's normal.

---

## 10. SAVE YOUR WORK (don't skip this)

The moment it moves cleanly:
- **Save To Device** — writes the config to the drive so it survives a power-cycle.
- **File → Save** the WorkBench project to your computer.

That saved file is your undo button. If the config ever gets scrambled, reload it
instead of rebuilding from scratch.

---

## 11. If something goes wrong

| Symptom | Most likely cause | Fix |
|---|---|---|
| Won't enable, says **STO** | A11 or B11 not at 24 V | Check both STO jumpers to B3 |
| Won't enable, says **hardware disable** | A5 not at 24 V | Jumper A5 to B3 |
| **Loud buzz + motor overload** on move | Bad commutation offset | Re-run **Auto** Wake & Shake, confirm ~100° |
| Autotune / motion fails after it worked | Commutation got clobbered | Re-run Auto Wake & Shake |
| Motor data fields greyed out | Motor Autoset is On | Set Autoset = 0 (Off) |
| Overloads easily / runs rough | Wrong Kt/Ke units or inductance | Check Ke÷Kt ≈ 60; inductance = 11.5 |
| **Start completely over** | Config tangled | Parameter Load/Save → Reset to Factory Defaults, then redo from Step 4 |

---

## 12. The short version (once you know it)

1. Add device → Motor (Autoset **Off**, enter MV43 values, Create Motor)
2. Power = 480 V / 3-phase → Motor Temp = 127 → Feedback = match Identified → Brake = Not Used
3. **Auto** Wake & Shake → confirm **~100° Successful**
4. Units = 4 mm lead → Home = current position
5. Jog at low speed → Autotune
6. **Save To Device + save the project file**

The one rule to remember: **always use Auto Wake & Shake, and start every move slow.**
