# Turn a Raspberry Pi Into a PLC Using OpenPLC

> **Source:** [control.com — Dr. Don Wilcher (Feb 21, 2024)](https://control.com/technical-articles/turn-a-raspberry-pi-into-a-plc-using-openplc/)

Using a Raspberry Pi and the OpenPLC software platform, create a simple PLC that can be programmed in ladder diagrams with remote access and I/O monitoring dashboards.

---

## Overview

OpenPLC provides a control engineering development platform that transforms various microcontrollers into programmable logic controllers. It is compatible with Arduino Uno, ESP32, RP2040, and single-board computers like the Raspberry Pi — using an editor, a runtime engine, and a web server.

---

## 1. OpenPLC Runtime on the Raspberry Pi

The OpenPLC runtime has an integrated web server for configuring runtime parameters. Key data types include:

| Tag | Type       | Size     |
|-----|------------|----------|
| X   | Bit        | 1-bit    |
| B   | Byte       | 8-bits   |
| W   | Word       | 16-bits  |
| D   | Double Word| 32-bits  |
| L   | Long Word  | 64-bits  |

Access the runtime web server using:

```text
http://YOUR_PI_IP_ADDRESS:8080
```

> Find your Pi's IP address by hovering over the Wi-Fi icon in the taskbar.

---

## 2. Prerequisites

### 2a. WiringPi GPIO Library

Check if the WiringPi library is installed:

```bash
gpio -v
```

If not found, install it:

```bash
git clone https://github.com/WiringPi/WiringPi.git
cd WiringPi
./build
```

Verify the install again:

```bash
gpio -v
```

### 2b. OpenPLC Runtime

Return to the home directory:

```bash
cd
```

Clone the OpenPLC repository:

```bash
git clone https://github.com/thiagoralves/OpenPLC_v3.git
```

Enter the directory:

```bash
cd OpenPLC_v3
```

Run the installation script (this takes several minutes):

```bash
./install.sh rpi
```

Once complete, navigate to `http://YOUR_PI_IP:8080` in a browser — the runtime login screen should appear.

> For more thorough documentation, see the [OpenPLC official website](https://autonomylogic.com/docs/installing-openplc-runtime-on-linux-systems/).

---

## 3. Pin Mapping: Raspberry Pi → PLC

OpenPLC uses the **body-pin format** (not GPIO numbers) for I/O addressing.

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

This example project uses:
- A **tactile pushbutton switch** with a **10kΩ pulldown resistor** (input)
- A **330Ω resistor** in series with an **LED** (output)

Connections:
- **+3.3V** → breadboard power rail
- **GND** → breadboard ground rail
- **Pin 11 (GPIO 17)** → pushbutton input
- **Pin 16 (GPIO 23)** → LED output

An extension/breakout board with a ribbon cable can be used to simplify wiring to the 40-pin header. Alternatively, use jumper wires directly on the Pi header.

---

## 5. Writing the Ladder Logic (OpenPLC Editor)

1. Install the **OpenPLC Editor** on your computer (not the Pi):  
   https://autonomylogic.com/download

2. Create a new **"Hello World" Ladder Diagram (LD)** project.

3. Assign I/O tags using the **physical body-pin addressing**:
   - Input: `IX0.3` → Pin 11 (pushbutton)
   - Output: `QX0.2` → Pin 16 (LED)

4. Export the program as a **`.st` (structured text) file** using the orange download arrow in the editor toolbar.

---

## 6. Uploading and Running the Program

### Set Hardware Layer

1. Open the runtime at `http://YOUR_PI_IP:8080`
2. Log in with default credentials:
   - **Username:** `openplc`
   - **Password:** `openplc`
3. Go to **Hardware** → select **Raspberry Pi** → click **Save Changes**

### Upload the Program

1. Go to **Programs** in the left panel
2. Click **Choose File** → select your `Hello World.st` file
3. Click **Upload Program**

The `.st` file will be compiled to C++ automatically.

### Start the PLC

1. Go to **Dashboard**
2. Click **Start PLC**

### Monitor I/O

1. Click **Monitor** to observe pushbutton and LED states in real time
2. Each press of the pushbutton toggles the LED (red → green in the monitor)

> The Monitor can serve as a simple HMI/diagnostic tool for watching physical I/O operation.

---

## Reference

- [OpenPLC Runtime Documentation](https://autonomylogic.com/docs/installing-openplc-runtime-on-linux-systems/)
- [OpenPLC Physical Addressing](https://autonomylogic.com/docs/2-4-physical-addressing/)
- [Original Article — control.com](https://control.com/technical-articles/turn-a-raspberry-pi-into-a-plc-using-openplc/)
- [Video Demo](https://youtu.be/JvlNExM0f0I)
