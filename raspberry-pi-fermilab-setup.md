# Raspberry Pi Setup + Fermilab WiFi + SSH Guide

## 1. Install Raspberry Pi Imager

Download Raspberry Pi Imager here:  
https://www.raspberrypi.com/software/

Install and open the application.

---

## 2. Prepare microSD Card

- Insert microSD card into your computer
- Open Raspberry Pi Imager

---

## 3. Flash Raspberry Pi OS

### Select Operating System

Choose:
- Raspberry Pi OS (64-bit)

### Select Storage

Choose your microSD card

---

## 4. Configure Settings (IMPORTANT)

Click the settings (gear icon) before writing.

### General

- Hostname: `mypi`
- Username: choose something simple
- Password: set a memorable password

### Location

- Timezone: `America/Chicago`
- Location: Washington, DC

### Network

- SSID: `fgz`
- Network type: Open network

### Services

- Enable SSH

---

## 5. Write to SD Card

Click **Write** and wait:
- ~10–15 minutes
- Includes verification

---

## 6. First Boot

Insert SD card into Raspberry Pi and connect:
- Power
- HDMI
- Keyboard (optional)

Boot time: ~2–3 minutes

---

## 7. Find MAC Address (WiFi Registration)

Run on the Pi:

```bash
ifconfig -a
```
