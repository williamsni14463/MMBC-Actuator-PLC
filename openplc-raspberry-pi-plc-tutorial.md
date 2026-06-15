# Turn a Raspberry Pi Into a PLC Using OpenPLC

> **Source:** [control.com — Dr. Don Wilcher (Feb 21, 2024)](https://control.com/technical-articles/turn-a-raspberry-pi-into-a-plc-using-openplc/)

Using a Raspberry Pi and the OpenPLC software platform, create a simple PLC that can be programmed in ladder diagrams with remote access and I/O monitoring dashboards.

---

## Overview

I will do my best to summarize the steps to this test and provide some help, but try to follow the tutorial to your best ability and debug/research when things go wrong to better understand.

---

## 1. OpenPLC Runtime on the Raspberry Pi

The OpenPLC runtime has an integrated web server for configuring runtime parameters, we accessed this in the previous section.
Access the runtime web server using:

```text
http://YOUR_PI_IP_ADDRESS:8080
```

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

This example project uses:
- A **pushbutton switch** with a **10kΩ resistor** (input)
- A **330Ω resistor** in series with an **LED** (output)
  > We only have 220Ω & 10kΩ resistors, the 220Ω will work just fine in place of the 330Ω.
  

Connections:
- **+3.3V** → breadboard power rail
- **GND** → breadboard ground rail
- **Pin 11 (GPIO 17)** → pushbutton input
- **Pin 16 (GPIO 23)** → LED output

This tutorial uses an extension/breakout board with a ribbon cable to simplify wiring to the 40-pin header. 

We dont have one of these, so use jumper wires directly onto the Raspberry Pi GPIO

---

## 5. Writing the Ladder Logic (OpenPLC Editor)

1. Create a new project in the OpenPLC Editor using the language Ladder Diagram
   > Be sure to NOT save in OneDrive

2. Assign I/O tags using the variable declaration section:
   Variable #1:
   Name: PB1_Switch | Class: Local | Type: BOOL | Location: %IX0.3 |

   Variable #2:
   Name: Hello_World_LED | Class: Local | Type: BOOL | Location: %QX0.2 |

3. Add a rung to the ladder diagram and create the following
4. <img width="800" height="358" alt="image" src="https://github.com/user-attachments/assets/87864bdd-56f0-4dce-affc-0c3e91a000d9" />


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
