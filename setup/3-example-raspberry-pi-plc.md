# Example: Turn a Raspberry Pi Into a PLC Using OpenPLC

> **Source:** [control.com — Dr. Don Wilcher (Feb 21, 2024)](https://control.com/technical-articles/turn-a-raspberry-pi-into-a-plc-using-openplc/)

This is a hello-world style project — a pushbutton that controls an LED through the PLC. It confirms everything is working before you go further.

I summarized the steps and added notes for our specific setup (different resistors, no breakout board, etc.). Try to follow along with the original article too and debug/research when things go wrong — it'll help you actually understand what's happening.

---

## 1. Access the Runtime

The OpenPLC runtime has a built-in web server. Access it at:

```
http://YOUR_PI_IP_ADDRESS:8080
```

---

## 2. Prerequisites

### WiringPi GPIO Library

Check if it's installed:

```
gpio -v
```

If not found, install it:

```
git clone https://github.com/WiringPi/WiringPi.git
cd WiringPi
./build
```

Verify again:

```
gpio -v
```

---

## 3. Pin Mapping: Raspberry Pi → PLC

OpenPLC uses the **body-pin format** for I/O addressing.

### Inputs (left-side pins, odd numbers)

| Body Pin | GPIO Pin | OpenPLC Tag |
|----------|----------|-------------|
| 3        | GPIO 2   | IX0.0       |
| 5        | GPIO 3   | IX0.1       |
| 7        | GPIO 4   | IX0.2       |
| 11       | GPIO 17  | IX0.3       |
| 13       | GPIO 27  | IX0.4       |

### Outputs (right-side pins, even numbers)

| Body Pin | GPIO Pin | OpenPLC Tag |
|----------|----------|-------------|
| 8        | GPIO 14  | QX0.0       |
| 10       | GPIO 15  | QX0.1       |
| 16       | GPIO 23  | QX0.2       |
| 18       | GPIO 24  | QX0.3       |
| 22       | GPIO 25  | QX0.4       |

---

## 4. Wiring the Circuit

This example uses:
- A **pushbutton switch** with a **10kΩ resistor** (input)
- A **330Ω resistor** in series with an **LED** (output)

> We only have 220Ω & 10kΩ resistors — the 220Ω works fine in place of the 330Ω.

Connections:
- **+3.3V** → breadboard power rail
- **GND** → breadboard ground rail
- **Pin 11 (GPIO 17)** → pushbutton input
- **Pin 16 (GPIO 23)** → LED output

The tutorial uses a breakout board with a ribbon cable for the 40-pin header. We don't have one, so just use jumper wires directly on the Pi's GPIO pins.

---

## 5. Writing the Ladder Logic (OpenPLC Editor)

1. Create a new project in the OpenPLC Editor — use the language **Ladder Diagram**
   > Be sure NOT to save the project in OneDrive — it can cause path issues when uploading.

2. Assign I/O tags in the variable declaration section:

   | Name | Class | Type | Location |
   |------|-------|------|----------|
   | PB1_Switch | Local | BOOL | %IX0.3 |
   | Hello_World_LED | Local | BOOL | %QX0.2 |

3. Add a rung to the ladder diagram — connect `PB1_Switch` as a contact and `Hello_World_LED` as a coil. When the button is pressed, the LED turns on.

---

## 6. Uploading and Running the Program

### Start the Runtime

SSH into the Pi and run:

```
cd OpenPLC_v3
sudo ./start_openplc.sh
```

### Set the Hardware Layer

1. Open `http://YOUR_PI_IP:8080`
2. Log in (openplc / openplc)
3. Go to **Hardware** → select **Raspberry Pi** → click **Save Changes**

### Connect the Editor to the Runtime

1. In the Editor, go to **Device → Configuration** (top left)
2. Set Device to **OpenPLC Runtime v3**
3. Enter the Pi's IP address (from `hostname -I`)
4. Connect

> It may ask for credentials — use openplc / openplc or whatever you set.

### Upload the Program

1. In the runtime web UI, go to **Programs** in the left panel
2. Click **Choose File** → find your `.st` file

   > The `.st` file is generated when you build the project. Navigate to: `Project Folder → build → OpenPLC Runtime v3 → src → program_name.st`

3. Click **Upload Program**

The `.st` file compiles to C++ automatically — wait for it.

### Start the PLC

1. Go to **Dashboard**
2. Click **Start PLC**

### Monitor I/O

1. Click **Monitor** to watch the pushbutton and LED states in real time
2. Each press of the pushbutton should toggle the LED (False → True in the monitor)

> The Monitor is super useful as a diagnostic tool — if the button shows as True but the LED doesn't light up, it's probably a wiring issue.

---

## References

- [OpenPLC Runtime Documentation](https://autonomylogic.com/docs/installing-openplc-runtime-on-linux-systems/)
- [OpenPLC Physical Addressing](https://autonomylogic.com/docs/2-4-physical-addressing/)
- [Original Article — control.com](https://control.com/technical-articles/turn-a-raspberry-pi-into-a-plc-using-openplc/)
- [Video Demo](https://youtu.be/JvlNExM0f0I)

---

**Setup complete!** Head over to [experiments/](../experiments/) to see what I've been testing.
